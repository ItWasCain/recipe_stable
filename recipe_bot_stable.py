# CREATE TABLE recipes_links_list(
# id BIGSERIAL NOT NULL PRIMARY KEY,
# recipe_name VARCHAR(100) NOT NULL,
# recipe_link VARCHAR(150) NOT NULL
# );
#
# CREATE TABLE users_requests_list(
# user_id VARCHAR(100),
# recipe_name_1 VARCHAR(100),
# recipe_name_2 VARCHAR(100),
# recipe_name_3 VARCHAR(100),
# recipe_name_4 VARCHAR(100),
# recipe_name_5 VARCHAR(100)
# );
import requests
import bs4
import telebot
import os
import os.path
import psycopg2
# from telebot import types
from base64 import decode


TOKEN = ''
bot = telebot.TeleBot(TOKEN)

host = '127.0.0.1'
user = 'postgres'
password = '1234'
db_name = 'recipes'
port = 5432
connection = ''


def parse(url, user_id):

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 OPR/82.0.4227.50'
    }
    response = requests.get(url, headers = HEADERS)
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
 
    items = soup.find_all('h3', class_ = 'item-title')
    user_id = str(user_id)
    urls = {}
    urls_list = []
    rec_names = []
    id_list = []
    id_rec_list = []
    for item in items:
        conts = item.find_all('a')

        for cont in conts:
            if cont.text.strip() != '':

                href = cont.get('href')
                rec_names.append(cont.text.strip())
                urls_list.append('https://eda.ru' + href)

        if len(urls_list) > 4:
            break
    # Если количество рецептов меньше 5, в список добавляются пустые строки чтобы длина списка была равна 5
    # В начало другого списка добавляется id пользователя
    # добавляется в конец списка, если он короче 5
    k = 5 - len(rec_names)
    k_list = list(('',) * k)
    # Подключение к таблице
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True

        # Загрузка данных в таблицы

        with connection.cursor() as cursor:

            for rec in rec_names:
                if rec == '':
                    break
                rec_ind = rec_names.index(rec)
                urls = urls_list[rec_ind]
                name_link = [rec] + [urls]

                # если такой рецепт уже есть, он пропускается
                cursor.execute(
                    """SELECT * FROM recipes_links_list WHERE recipe_name = (%s)""", [rec]
                )
                # если нет, он вставляется и ему присваивается уникальный id
                if cursor.fetchone() == None:
                    cursor.executemany(
                        """INSERT INTO recipes_links_list (recipe_name, recipe_link)"""
                        """VALUES (%s,%s)""", [(name_link),]
                    )
                    print('Рецепт ', name_link[0], ' добавлен')
                else:
                    print('[INFO] Data already inserted')
                # вывод id по названию в список

                cursor.execute(
                    """SELECT id FROM recipes_links_list WHERE recipe_name = (%s)""", [rec]
                )

                id_list.append(cursor.fetchone()[0])
            # Вставка списка из user id и id запросов в таблицу запросов пользователя. Если запрос от пользователя уже был, он удаляется и добавляется новый.
            cursor.execute(
                """SELECT * FROM users_requests_list WHERE user_id = (%s)""", [user_id]
            )
            if cursor.fetchone() != None:
                cursor.execute(
                    """DELETE FROM users_requests_list WHERE user_id = (%s)""", [user_id]
                )
            cursor.executemany(
                """INSERT INTO users_requests_list (user_id, recipe_name_1, recipe_name_2, recipe_name_3, recipe_name_4, recipe_name_5)"""
                """VALUES (%s,%s,%s,%s,%s,%s)""", [[user_id] + id_list + k_list,]
            )
            print('[INFO] Data inserted')

    except Exception as _ex:
        print('[INFO] ERROR PostgreSQL', _ex)
    finally:
        if connection:
            connection.close()
            # print('[INFO] PostgreSQL connection closed')

#Функция вывода всех запросов пользователя по его id


def user_request(user_id):
    try:
        # connect to database
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True

        with connection.cursor() as cursor:

            cursor.execute(
                """SELECT recipe_name_1, recipe_name_2, recipe_name_3, recipe_name_4, recipe_name_5
                FROM users_requests_list 
                WHERE user_id = (%s)""", [user_id]
            )
            request = cursor.fetchone()
            request = list(filter(None, request))
    except Exception as _ex:
        print('[INFO] ERROR PostgreSQL', _ex)
    finally:
        if connection:
            connection.close()
            # print('[INFO] PostgreSQL connection closed')
    # если запросов нет, возвращается ошибка

    if len(request) == 0:
        return 'Error'
    else:
        return request

# поиск названия и ссылки рецепта по его id
def recipe_name_search(recipe_id):
    try:
        # connect to database
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True

        with connection.cursor() as cursor:

            cursor.execute(
                """SELECT recipe_name, recipe_link
                FROM recipes_links_list
                WHERE id = (%s)""", [recipe_id]
            )

            request = cursor.fetchone()

    except Exception as _ex:
        print('[INFO] ERROR PostgreSQL', _ex)
    finally:
        if connection:
            connection.close()
            # print('[INFO] PostgreSQL connection closed')

    if request == None:
        return 'Error'
    else:
        return list(request)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, f'Рецепт какого блюда вы хотите получить?')

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    
    user_id = str(message.from_user.id)    
    text = str(message.text)
    msg = 'https://eda.ru/recipesearch?q=' + text

    parse(msg, user_id)

    id_list = user_request(str(message.from_user.id))
    if id_list == 'Error':
        bot.send_message(message.chat.id, text='Рецепт не найден.')
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for recipe_id in list(id_list):
            button_text = recipe_name_search(recipe_id)
            markup.add(telebot.types.InlineKeyboardButton(text = button_text[0], callback_data = str(recipe_id)))
        #
        bot.send_message(message.chat.id,text = 'Выберите рецепт:', reply_markup=markup)
#
#
@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id)
    recipe_name_link = recipe_name_search(str(call.data))
    if recipe_name_link == 'Error':
        bot.send_message(call.message.chat.id, text='Обновите список.')
    else:
        recipe_link = recipe_name_link[1]

        bot.send_message(call.message.chat.id, recipe_link)
#
# #
# #
if __name__ == '__main__':
    bot.polling(none_stop=True)
