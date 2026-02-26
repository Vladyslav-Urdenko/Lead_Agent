import asyncio
from app.services.scraper import scrape_company_website
from app.services.ai_engine import analyze_text, generate_email

# Твое предложение (IoT)
MY_OFFER = """
Мы производим промышленные шлюзы (Gateways) с поддержкой Edge Computing. 
Позволяют обрабатывать данные с датчиков локально, не отправляя все в облако, 
что экономит трафик на 40% и повышает безопасность. Поддержка Docker-контейнеров на борту.
"""

async def main():
    # 1. Скармливаем сайт (возьмем для примера сайт Advantech или любого интегратора)
    target_url = "https://www.advantech.com/en" 
    print(f"1. Парсим сайт: {target_url}...")
    
    scrape_result = await scrape_company_website(target_url)
    raw_text = scrape_result.get("raw_text", "")
    
    if not raw_text:
        print("Ошибка: Не удалось скачать текст сайта.")
        return

    print("Текст получен. Длина:", len(raw_text))

    # 2. Анализируем через ИИ
    print("\n2. ИИ Анализирует компанию...")
    analysis = await analyze_text(raw_text)
    
    if not analysis:
        print("Ошибка: Не удалось проанализировать текст.")
        return

    print(f"\n--- Отчет Аналитика ---")
    print(f"Компания: {analysis.summary}")
    print(f"Стек: {analysis.tech_stack}")
    print(f"Боли: {analysis.pain_points}")
    print(f"Хук: {analysis.suggested_hook}")

    # 3. Пишем письмо
    print("\n3. Генерация письма...")
    email_draft = await generate_email(analysis, MY_OFFER)
    
    print(f"\n--- ЧЕРНОВИК ПИСЬМА ---\n")
    print(email_draft)
    print("\n-----------------------")

if __name__ == "__main__":
    asyncio.run(main())
