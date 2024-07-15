# Attention Message Sender
## Описание
Скрипт используется в качестве ассистента для контроля информации, которая отображается по ордерам в таблице продаж.
Скрипт использует Google API для получения доступа к Google Sheets, а так же Telegram API для отправки информации 
в рабочие чаты.

## Установка
1. `git clone https://github.com/ltrix07/Attention-Message-Sender.git`
2. `python3 -m venv venv`
3. `source venv/bin/activate`
4. `pip3 install -r requirements.txt`
5. Создать директорию `creds`:
   1. Создать файл `google_creds.json`. В нем должен хранится ключ от сервисной почты Google.
   2. Создать файл `telegram.json`. В нем должен хранится токен бота, который будет слать сообщения. Формат такой:  
```json
{
  "token": "<token>"
}
```
6. Создать директорию `db`:
   1. Создать файл `chat_data.json`. В нем должны хранится id тех чатов, в которые будет отправляться сообщение того или
иного типа.
   2. Создать файл `spreadsheets.json`. В него будет сохранятся вся ифнормация после добавление таблицы через файл [maneger.py](maneger.py)
   3. Создать файл `staff.json`. В нем должны хранится никнеймы работников в телеграм.  
7. `python3 maneger.py`. Добавить данные про таблицы (будут просматриваться циклом).  
8. `python3 main.py`  

Вид файла `chat_data.json`:
```json
{
  "chat_w_problems": "id чата, в который будут отправляться сообщения с ошибкой",
  "chat_w_attentions": "id чата, в который будут отправляться сообщения, на которые надо обратить внимание"
}
```

Вид файла `spreadsheets.json` (будет заполняться полуавтоматически):
```json
{
  "test": {
    "table_id": "<table_id>",
    "columns": {
      "status1": "Status 1",
      "purchase_date": "Date of purchase",
      "profit_amount": "Profit with gift",
      "perc_profit": "Profit (%)",
      "perc_w_gift": "Profit with gift %",
      "order_num": "Order ID Amazon",
      "buy_price": "Buy price"
    }
  }
}
```

Вид файла `staff.json`:
```json
{
  "analysts": ["worker1", "worker2"],
  "buyers": ["worker1", "worker2"],
  "developers": ["worker1", "worker2"],
  "trackers": ["worker1", "worker2"]
}
```


## Алгоритм
Бот использует следующий алгоритм действий:
1. Определяет все нужные ему для работы директории внутри проекта. За это отвечает функция [main()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/main.py#L75).
2. Читает файлы, в которых записана информация про чаты и таблицы. Функция [process()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/main.py#L57).  
Чтение происходит из двух файлов - `creds/telegram.json` (чаты телеграм, в которые надо отправлять сообщения) и `db/spreadsheets.json`
   (информация про таблицы, с которых надо получать информацию).
3. Просмотр таблицы целиком обозначение какие листы есть, каких нет. За это отвечает функция [look_table()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/main.py#L29).
Если нет листа с текущим месяцем, бот отправит сообщение:  
```text
@worker1, worker2
В таблице "10" нет листа с текущим месяцем.
```
_Следовательно, стоит называть листы номерами месяцев_. 

Под сообщением будет кнопка `Я добавил лист`. После того как работник создал лист и в названии указал текущий месяц он должен
нажать эту кнопку. Это даст боту понять что человек исправил ошибку и в случае если он встретит ее снова, то нужно опять отправить
информацию в чат.
4. Бот приступает к обработке каждого интересующего листа (текущий месяц, прошлый месяц, азат текущий м., азат прошлый м.
бро текущий м., бро прошлый м.). За эту обработку отвечает функция [sheet_look()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/main.py#L16).
5. Собирается вся информация с листа при помощи метода [get_all_info_from_sheet()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/main.py#L22).
6. Определяются индексы тех столбцов, информация с которых нам нужна. При помощи метода [get_columns_indices()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/main.py#L23).
7. Общие полученные данные фильтруются относительно индексов. При помощи метода [filter_data_by_indices()](https://github.com/ltrix07/Attention-Message-Sender/blob/0db497da31a28a04e1d15c4ece5224c244f05794/attention_sender/inspections.py#L22).