from flask import Flask, request, jsonify
from twilio.rest import Client
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Restaurant configuration
RESTAURANT_NAME = "Gourmet Delight"
MENU_PDF_URL = "https://your-public-pdf-url.com/menu.pdf"

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
        if 'menu' in incoming_msg or 'pdf' in incoming_msg:
            try:
                twilio_client.messages.create(
                    media_url=[MENU_PDF_URL],
                    from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
                    to=sender,
                    body=f"Here's the menu for {RESTAURANT_NAME}! 🍽️"
                )
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Case 2: General question
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4.1",
                #model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant for {RESTAURANT_NAME}."},
                    {"role": "user", "content": incoming_msg}
                ]
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
    
