Управление рассылкой по следующим телеграм каналах:
1) -1001470907718: https://t.me/joinchat/lALn2_ctqAtkMDZi
2) -1001294452856: https://t.me/joinchat/tHawW9RZAFoyODli
3) -1001252485999: https://t.me/joinchat/6JyZDgpiQXdjM2Qy
4) -1001367691516: https://t.me/joinchat/0QAbGoARA0A3ODIy
5) -1001420568474: https://t.me/joinchat/jkD7-PO8qtoxYjcy
6) -1001222952410: https://t.me/joinchat/23GYv93TBKI1ODky
7) -1001464760193: https://t.me/joinchat/mXpbOwn3EHUzYmM6
8) -1001351980116: https://t.me/joinchat/cuh2rak2sKNhNTNi
9) -1001467928277: https://t.me/memes_smeshnye_video


Администрирование ботом происходит с помощью бота @Meme1RobotAdminBot

-----

Сначала с файла action.txt будет считано действие. Сначала это меню.
Если робота прерветься во время автопоста, то при запуске бота следующий раз автоматичесски будет включен автопост.

-----

Меню:
* 1) /mailing - Рассылка сообщения по всем чатам
* 2) /fill_channels - начать заполнение каналов по 300 лучших постов
* 3) /autopost - начать монитроринг новых постов и их отправку по расписанию
* 4) /send_post - отправляет по одному новому посту в каждый возможный канал

-----

### 1) /mailing - Рассылка сообщения по всем чатам
1. Бот попросит ввести сообщение, которое будет разослано по всем каналам


#### 2) /fill_channels - начать заполнение каналов по 300 лучших постов
1. Сначала из приложение считываються все посты
2. Затем из каждого канала вытаскиваеться дата последней медиа-публикации
3. Програма отбирает все посты, которые были добавлены в приложение позже последней публикации канала
4. Посты сортируються от менее залайканого к болле залайканому
5. Если постов больше, чем 300 - береться300 лучшихб если меньше - беруться все
6. Проводиться проверка на наличие дубликатов по url поста. Дубликаты удаляються
7. Проводиться отправка постов по соответсвующим каналам
8. При наличие вотермарки приложение - она вырезаеться


#### 3) /autopost - начать монитроринг новых постов и их отправку по расписанию
1. Запускаеться автопостинг постов в каналы
2. Если время равно 9:00, 12:00 или 18:00 - идет рассылка по одному лучшему посту по каналам
3. Если время равно 8:00 - собираються мемы за вчера и добавляються в конец списка постов каждого канала
4. Чтобы отключить автопост необходимо отправить боту команду /stop. 
5. Пока автопост включен, другие функции недоступны.


### 4) /send_post - отправляет по одному новому посту в каждый возможный канал
1. Идет рассылка по одному лучшему посту по каналам




