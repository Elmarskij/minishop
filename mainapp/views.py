import operator
from functools import reduce
from itertools import chain
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.views.generic import DetailView, View
from .models import Category, Customer, Order, CartProduct, Product
from .mixins import CartMixin
from .forms import (OrderForm, LoginForm, RegistationForm, ProfileEditForm)
from .utils import recalc_cart
from specs.models import ProductFeatures


class MyQ(Q):

    default = 'OR'


class BaseView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        products = Product.objects.all()
        context = {
            'categories': categories,
            'products': products,
            'cart': self.cart,
        }
        return render(request, 'mainapp/base.html', context)


class ProductDetailView(CartMixin, DetailView):
    
    model = Product
    context_object_name = 'product'
    template_name = 'mainapp/product_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = self.get_object().category.__class__.objects.all()
        context['cart'] = self.cart
        return context
    

class CategoryDetailView(CartMixin, DetailView):

    model = Category
    queryset = Category.objects.all()
    context_object_name = 'category'
    template_name = 'mainapp/category_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('search')
        category = self.get_object()
        context['cart'] = self.cart
        context['categories'] = self.model.objects.all()
        if not query and not self.request.GET:
            context['category_products'] = category.product_set.all()
            return context
        if query:
            products = category.product_set.filter(Q(title__icontains=query))
            context['category_products'] = products
            return context
        url_kwargs = {}
        for item in self.request.GET:
            if len(self.request.GET.getlist(item)) > 1:
                url_kwargs[item] = self.request.GET.getlist(item)
            else:
                url_kwargs[item] = self.request.GET.get(item)
        q_condition_queries = Q()
        for key, value in url_kwargs.items():
            if isinstance(value, list):
                q_condition_queries.add(Q(**{'value__in': value}), Q.OR)
            else:
                q_condition_queries.add(Q(**{'value': value}), Q.OR)
        pf = ProductFeatures.objects.filter(
            q_condition_queries
        ).prefetch_related('product', 'feature').values('product_id')
        products = Product.objects.filter(id__in=[pf_['product_id'] for pf_ in pf])
        context['category_products'] = products
        return context


class AddToCartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)
        cart_product, created = CartProduct.objects.get_or_create(
            user=self.cart.owner, cart=self.cart, product=product,
        )
        if created:
            self.cart.products.add(cart_product)
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар успешно добавлен")
        return HttpResponseRedirect('/cart/')


class DeleteFromCartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, product=product,
        )
        self.cart.products.remove(cart_product)
        cart_product.delete()
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар успешно удален")
        return HttpResponseRedirect('/cart/')


class ChangeQuantityView(CartMixin, View):

    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, product=product,
        )
        quantity = int(request.POST.get('quantity'))
        cart_product.quantity = quantity
        cart_product.save()
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Количество товара успешно изменено")
        return HttpResponseRedirect('/cart/')


class CartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        context = {
            'cart': self.cart,
            'categories': categories,
        }
        return render(request, 'mainapp/cart.html', context)


class CheckoutView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        form = OrderForm(request.POST or None)
        context = {
            'cart': self.cart,
            'categories': categories,
            'form': form,
        }
        return render(request, 'mainapp/checkout.html', context)


class MakeOrderView(CartMixin, View):

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = OrderForm(request.POST or None)
        customer = Customer.objects.get(user=request.user)
        if form.is_valid():
            new_order = form.save(commit=False)
            new_order.customer = customer
            new_order.first_name = form.cleaned_data['first_name']
            new_order.last_name = form.cleaned_data['last_name']
            new_order.phone = form.cleaned_data['phone']
            new_order.address = form.cleaned_data['address']
            new_order.buying_type = form.cleaned_data['buying_type']
            new_order.order_date = form.cleaned_data['order_date']
            new_order.comment = form.cleaned_data['comment']
            new_order.save()
            self.cart.in_order = True
            self.cart.save()
            new_order.cart = self.cart
            new_order.save()
            self.cart.save()
            customer.orders.add(new_order)
            messages.add_message(request, messages.INFO, 'Спасибо за заказ!')
            return HttpResponseRedirect('/')
        return HttpResponseRedirect('/checkout/')


class LoginView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        categories = Category.objects.all()
        context = {'form': form, 'categories': categories, 'cart': self.cart,}
        return render(request, 'mainapp/login.html', context)
    
    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect('/')
        categories = Category.objects.all()
        context = {
            'form': form,
            'cart': self.cart,
            'categories': categories,
        }
        return render(request, 'mainapp/login.html', context)


class RegistrationView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        form = RegistationForm(request.POST or None)
        categories = Category.objects.all()
        context = {
            'form': form,
            'categories': categories,
            'cart': self.cart,
        }
        return render(request, 'mainapp/registration.html', context)
    
    def post(self, request, *args, **kwargs):
        form = RegistationForm(request.POST or None)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.username = form.cleaned_data['username']
            new_user.email = form.cleaned_data['email']
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.save()
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            Customer.objects.create(
                user = new_user,
                phone = form.cleaned_data['phone'],
                address = form.cleaned_data['address']
            )
            user = authenticate(username=new_user.username, password=form.cleaned_data['password'])
            login(request, user)
            return HttpResponseRedirect('/')
        categories = Category.objects.all()
        context = {
            'form': form,
            'cart': self.cart,
            'categories': categories,
        }
        return render(request, 'mainapp/registration.html', context)


class OrderView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        customer = Customer.objects.get(user=request.user)
        orders = Order.objects.filter(customer=customer).order_by('-created_at')
        categories = Category.objects.all()
        context = {
            'orderds': orders,
            'cart': self.cart,
            'categories':categories,
        }
        return render(request, 'mainapp/my_orders.html', context)


class ProfileView(CartMixin, View):
    
    def get(self, request, *args, **kwargs):
        user = Customer.objects.get(user=request.user)
        orders = Order.objects.filter(customer=user).order_by('-created_at')
        categories = Category.objects.all()
        context = {
            'user': user,
            'orders': orders,
            'cart': self.cart,
            'categories': categories,
        }
        return render(request, 'mainapp/profile.html', context)


def profile(request):
    user = Customer.objects.filter(user = request.user)
    if request.method == 'POST' :
        form = ProfileEditForm(request.POST or None)
        if form.is_valid():
            print("Valid")
            form.save(commit=True)
            messages.add_message(request, messages.INFO, 'Учетная запись успешно отредактирована!')
            return HttpResponseRedirect('/profile/')
    print("else")
    form = ProfileEditForm(user.values().first())
    context = {
    'user': user,
    'form': form,
    }
    messages.add_message(request, messages.INFO, 'Попробуйте еще раз!')
    return render(request, 'mainapp/profile_edit.html', context)
