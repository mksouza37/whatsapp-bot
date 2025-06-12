from flask import Flask, request, jsonify
from twilio.rest import Client
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Restaurant configuration
RESTAURANT_NAME = "Restaurante Gourmet IA"
MENU_PDF_URL = "https://dl.dropboxusercontent.com/scl/fi/fhclk798pmzghu8ozveb1/cardapio-pizzas.pdf?rlkey=5rxix01lbday155wq0rapxfrn&st=sldem1iq"

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

app = Flask(__name__)

def format_whatsapp_number(number):
    """Ensure WhatsApp numbers are in valid E.164 format"""
    if not number:
        return None
    return number.replace('whatsapp:', 'whatsapp:+') if not number.startswith('whatsapp:+') else number


@app.route('/whatsapp-webhook', methods=['POST'])
def whatsapp_webhook():
    try:
        # Debug logging
        print("\n=== INCOMING REQUEST ===")
        print("Headers:", request.headers)
        print("Form Data:", dict(request.form))

        incoming_msg = request.values.get('Body', '').lower()
        sender = format_whatsapp_number(request.values.get('From', ''))

        if not incoming_msg or not sender:
            return jsonify({'error': 'Missing Body or From'}), 400

        # Case 1: Menu request        
        menu_keywords = ['menu', 'pdf', 'cardápio', 'cardapio', 'carta', 'lista']
        if any(keyword in incoming_msg for keyword in menu_keywords):
            try:
                twilio_client.messages.create(
                    media_url=[MENU_PDF_URL],
                    from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
                    to=sender,
                    body=f"Aqui está o cardápio do {RESTAURANT_NAME}! 🍽️"
                )
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Case 2: General question
        try:
            system_message = f"""
                                You are an assistant for {RESTAURANT_NAME}. Your responsibilities include:
                                1. Offering to send our digital menu when customers ask
                                2. Answering questions about our restaurant
                                3. Providing friendly, concise responses
                                
                                When users request the menu:
                                - Confirm you'll send it
                                - Briefly mention 1-2 popular dishes
                                - Don't list the full menu (they'll see the PDF)
                                
                                For other questions:
                                - Keep answers under 2 sentences
                                - Be warm and professional
                                - Always answer in Portuguese                                
                                """           
            response = openai_client.chat.completions.create(                
                model="gpt-3.5-turbo",                
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": incoming_msg}
                ],
                temperature=0.7  # Adds slight creativity
            )

            reply = response.choices[0].message.content

        #except OpenAI.RateLimitError:
        #    reply = "⚠️ Sorry, our AI service is currently overloaded. Please try again later."
        except Exception as e:
            reply = f"⚠️ Error: {str(e)}"

        # Send response
        twilio_client.messages.create(
            body=reply,
            from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
            to=sender
        )
        return jsonify({'success': True})

    except Exception as e:
        print(f"!!! CRITICAL ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
    
