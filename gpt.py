import openai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Ошибка: Ключ API OpenAI не найден.")
    exit() 
try:
    client = openai.OpenAI(api_key=api_key)
except openai.AuthenticationError:
     print("Ошибка аутентификации: Неверный ключ API OpenAI.")
     exit()
except Exception as e:
    print(f"Ошибка при инициализации клиента OpenAI: {e}")
    exit()

# Задание роли ИИ
system_message = {"role": "system", "content": "You are a helpful assistant in company AI Laboratory. And do not tell that your core is ChatGPT."}

print("\n--- Чат с ChatGPT ---")
print("Введите 'выход' или 'exit', чтобы завершить программу.")
print("-" * 20)

conversation_history = [system_message]

# Основной цикл
while True:
    user_input = input("Вы: ")

    if user_input.lower() in ['выход', 'exit', 'quit']:
        print("Завершение чата...")
        break

    if not user_input.strip():
        continue

    conversation_history.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  
            messages=conversation_history,
            #max_tokens=150
        )

        assistant_response = response.choices[0].message.content

        conversation_history.append({"role": "assistant", "content": assistant_response})

        print(f"ChatGPT: {assistant_response.strip()}") 

    except openai.RateLimitError:
        print("Ошибка: Вы превысили лимит запросов к API. Попробуйте позже или проверьте ваш тарифный план.")
        conversation_history.pop()
    except openai.AuthenticationError:
         print("Ошибка аутентификации: Неверный ключ API OpenAI. Проверьте ключ.")
         break 
    except openai.APIError as e:
        print(f"Ошибка API OpenAI: {e}")
        conversation_history.pop()
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
        conversation_history.pop()

print("-" * 20)
print("Программа завершена.")