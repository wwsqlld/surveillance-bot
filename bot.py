import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
)

import firebase_admin
from firebase_admin import credentials, db

import instaloader







load_dotenv()





L = instaloader.Instaloader()


cred = credentials.Certificate("/etc/secrets/data-py-bot-firebase.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://data-py-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

ref = db.reference('/')



TOKEN = os.getenv('TOKEN')


class Form(StatesGroup):
    username = State()


form_router = Router()









# Добавление нового пользователя
def add_user(user_id, user_name, ifPrivat, ifStory, subscriptions, subscribers):
    ref.child(f'{user_id}').set({
            "target": f'{user_name}',
            "ifPrivat": f'{ifPrivat}',
            "ifStory": f'{ifStory}',
            "subscriptions": f'{subscriptions}',
            "subscribers": f'{subscribers}'
    })




# Функция для получения имени по ID
def get_name_by_id(user_id):
    name = ref.child(f'{user_id}').child('target').get()
    if name:
        return name
    else:
        return None




# Функция для удаления данных по ID
def delete_data_by_id(user_id):
    ref.child(f'{user_id}').delete()








@form_router.message(CommandStart())
async def command_start(message: Message, state: FSMContext) -> None:
    acc = get_name_by_id(message.from_user.id)
    if acc != None:
        await message.answer(f"Твой аккаунт: \n\nТы подписан на {acc}") 
    else:
        await state.set_state(Form.username)
        await message.answer(
        f"Привет, {message.from_user.first_name}. По идеи ты должен отправить мне имя пользователя инстаграм за которым ты хочешь следить.",
        reply_markup=ReplyKeyboardRemove(),)
           

    
    



@form_router.message(Form.username)
async def process_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    user_f_acc = message.text
    try:
        profile = instaloader.Profile.from_username(L.context, f"{user_f_acc}")
    except Exception as e:
        await message.answer("Аккаунт не найден. Напиши заново:")
    if profile.username:
        ifPrivat = profile.is_private
        ifStory = profile.has_public_story
        subscriptions = profile.followees
        subscribers = profile.followers
        add_user(user_id, user_f_acc, ifPrivat, ifStory, subscriptions, subscribers)
        await message.answer(f"Теперь ты подписан на {message.text}.\nТы будешь получать уведомления о любой активности аккаунта✅")
        await state.update_data(username=message.text)
        await state.clear()
        asyncio.create_task(infinite_function(message = message, user_id = user_id))

        
    else:
        return None
    




@form_router.message(Command('myaccount'))
async def account(message: Message) -> None:
    tar = get_name_by_id(message.from_user.id)
    await message.answer(f"Твой аккаунт: \n\nТы подписан на {tar}")





@form_router.message(Command('changetracking'))
async def changetracking(message: Message, state: FSMContext) -> None:
    delete_data_by_id(message.from_user.id)
    await state.set_state(Form.username)
    await message.answer(f"Напиши ник нового пользователя:")



@form_router.message(Command('infoabout'))
async def info(message: Message) -> None:
    target = get_name_by_id(message.from_user.id)
    profile = instaloader.Profile.from_username(L.context, f"{target}")
    ifPrivat = "приватный" if profile.is_private else "открытый"
    ifStory = "Есть актуальные сторис" if profile.has_public_story else "Нету актуальных сторис"
    subscriptions = f"Количество подписок - {profile.followees}"
    subscribers = f"Количество подписчиков - {profile.followers}"
    text2 = f"Информация о аккаунте:\nАккаунт: {ifPrivat}\n{ifStory}\n{subscriptions}\n{subscribers}"
    await message.answer(f"{text2}")



   
    

async def infinite_function(message, user_id):
    while True:
        await asyncio.sleep(60)
        try:
            name = ref.child(f'{user_id}').child('target').get()
            ifStory = ref.child(f'{user_id}').child('ifStory').get()
            boolStory = True if ifStory == "True" else False
            subscriptions = ref.child(f'{user_id}').child('subscriptions').get()

            profile = instaloader.Profile.from_username(L.context, f"{name}")

            if int(subscriptions) - int(profile.followees) > 0:
                await message.answer(f"\nПользователь {name} от кого-то отписался\n")
                add_user(user_id, name, profile.is_private, profile.has_public_story, profile.followees, profile.followers)
            elif int(subscriptions) - int(profile.followees) < 0:
                await message.answer(f"\nПользователь {name} на кого-то подписался)\n")
                add_user(user_id, name, profile.is_private, profile.has_public_story, profile.followees, profile.followers)
        
            if boolStory != profile.has_public_story and boolStory == False:
                await message.answer(f"\nПользователь {name} опубликовал сторис\n")
                add_user(user_id, name, profile.is_private, profile.has_public_story, profile.followees, profile.followers)

        except Exception as e:
            await message.answer(f"Ошибка: {e}")
        
        
          








# Настройки
async def main() -> None:
   

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp = Dispatcher()

    dp.include_router(form_router)
    await dp.start_polling(bot)
    
    
    


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())