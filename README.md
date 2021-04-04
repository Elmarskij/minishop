# minishop
For Sunrise IT company
1. Склонировать репозиторий по следующим ссылка:
2. HTTPS: https://github.com/Elmarskij/minishop.git
3. SSH: git@github.com:Elmarskij/minishop.git
4. GitHub CLI: gh repo clone Elmarskij/minishop
5. Прописать следующие команды:
6. pip install -r requirements.txt
7. python manage.py makemigrations
8. python manage.py migrate
9. Запустить сервер: python manage.py runserver
--------------------------------------------------  
10.  Создание характеристик для товара
11. Зайти в админку и создайте несколько товаров в Products
12. Перейдите на главную страницу сайта. Кликните в навигации на имя пользователя и выберите "Редактирование товаров"
13. После этого вы попадете на страницу админки характеристик:
14. Сначала необходимо создать характеристику и выбрать категорию, к которой она относится
15. После этого необходимо создать для этой характеристики значение
16. Как только все вышеперечисленное сделали, можно переходить к следующей ссылке - создание характеристики для самого товара.
17. Далее можно будет редактировать характеристики товара.

---------------------
Postgre(minishop_db):
superuser: admin
password: minishop;
superuser(reserve): elmar
password: minishop
