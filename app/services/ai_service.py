import os
from flask import current_app

def get_ai_response(messages, system_prompt=None):
    api_key = current_app.config.get('OPENAI_API_KEY', '')
    if not api_key:
        return get_mock_response(messages[-1]['content'] if messages else '')

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        system = system_prompt or (
            "You are FinPilot, an expert AI finance assistant. You help with financial analysis, "
            "budgeting, forecasting, expense management, and strategic financial decisions. "
            "Be concise, professional, and data-driven. Format responses with markdown when helpful."
        )
        full_messages = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI service error: {str(e)}. Please check your OpenAI API key in settings."


def get_mock_response(user_message):
    msg = user_message.lower()
    if any(w in msg for w in ['expense', 'spending', 'cost']):
        return ("**Expense Analysis** 📊\n\nBased on your recent data:\n\n"
                "- **Top category**: Technology (32% of spend)\n"
                "- **Month-over-month**: +8.2% increase\n"
                "- **Recommendation**: Review software subscriptions for potential consolidation\n\n"
                "To get a detailed breakdown, try asking: *'Show me my top 5 expense categories'*")
    elif any(w in msg for w in ['revenue', 'income', 'profit']):
        return ("**Revenue Insights** 💹\n\nCurrent financial snapshot:\n\n"
                "- **Revenue trend**: +12% YoY growth\n"
                "- **Gross margin**: ~68%\n"
                "- **Net profit margin**: ~23%\n\n"
                "Your business is performing above industry average. Consider reinvesting in growth channels.")
    elif any(w in msg for w in ['budget', 'forecast', 'predict']):
        return ("**Budget & Forecast** 🎯\n\nQ4 Projection:\n\n"
                "- Expected revenue: **$485,000**\n"
                "- Projected expenses: **$312,000**\n"
                "- Forecasted profit: **$173,000**\n\n"
                "⚠️ Marketing budget is 78% utilized — consider rebalancing allocations.")
    elif any(w in msg for w in ['invoice', 'payment', 'receivable']):
        return ("**Invoice Status** 📋\n\n"
                "- **Outstanding**: 3 invoices ($28,500)\n"
                "- **Overdue**: 1 invoice ($4,200 — 15 days past due)\n"
                "- **Action needed**: Send payment reminder to overdue clients\n\n"
                "Average collection period: **32 days** (industry avg: 45 days) ✅")
    elif any(w in msg for w in ['risk', 'concern', 'problem', 'issue']):
        return ("**Risk Assessment** ⚠️\n\nKey financial risks identified:\n\n"
                "1. **Cash flow gap** — projected shortfall in March\n"
                "2. **Concentration risk** — 40% revenue from single client\n"
                "3. **Rising OpEx** — expenses growing faster than revenue\n\n"
                "**Recommendations:**\n"
                "- Diversify client portfolio\n- Negotiate extended payment terms\n- Review fixed costs")
    else:
        return ("I'm **FinPilot**, your AI finance copilot! 🚀\n\n"
                "I can help you with:\n"
                "- 📊 **Financial analysis** — trends, patterns, anomalies\n"
                "- 💰 **Expense management** — categorization and optimization\n"
                "- 📈 **Forecasting** — revenue and cash flow predictions\n"
                "- 📋 **Invoice tracking** — payment status and reminders\n"
                "- 🎯 **Budget planning** — allocation and variance analysis\n"
                "- 📑 **Report generation** — executive summaries\n\n"
                "What financial question can I answer for you today?")


def analyze_financial_data(data_summary):
    messages = [{"role": "user", "content": f"Analyze this financial data and provide insights:\n{data_summary}"}]
    return get_ai_response(messages, system_prompt=(
        "You are a CFO-level financial analyst. Provide structured insights with key metrics, "
        "anomalies, recommendations, and risk indicators. Use markdown formatting."
    ))


def generate_report_summary(report_data):
    messages = [{"role": "user", "content": f"Generate an executive summary for:\n{report_data}"}]
    return get_ai_response(messages, system_prompt=(
        "You are a senior financial executive. Write a concise executive summary with "
        "highlights, concerns, and strategic recommendations. Professional tone, markdown format."
    ))
