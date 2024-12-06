import os
import base64
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from together import Together
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
together_api_key = os.getenv('TOGETHER_API_KEY')

# Set up Together API client
together_client = Together(api_key=together_api_key)

# Define image generation parameters
quality_params = {
    "low": {
        "model": "black-forest-labs/FLUX.1-dev",
        "width": 512,
        "height": 384,
        "steps": 20,
        "n": 1,
        "response_format": "b64_json"
    },
    "mid": {
        "model": "black-forest-labs/FLUX.1-dev",
        "width": 768,
        "height": 576,
        "steps": 24,
        "n": 1,
        "response_format": "b64_json"
    },
    "high": {
        "model": "black-forest-labs/FLUX.1-dev",
        "width": 1024,
        "height": 768,
        "steps": 28,
        "n": 1,
        "response_format": "b64_json"
    }
}

# Initialize Telegram Bot
bot = Bot(token=telegram_token)

# Store current prompt in memory
user_data = {}

def start(update, context):
    """
    /start command handler to show welcome message
    """
    welcome_message = (
        "🎨 *Welcome to AI Image Generator Bot!* 🖌️\n\n"
        "I can help you create stunning images using advanced AI technology. "
        "Simply send me a text prompt, and choose your desired image quality!\n\n"
        "🌟 Features:\n"
        "- Text-to-Image Generation\n"
        "- Multiple Quality Options\n"
        "- Easy Social Sharing\n\n"
        "Examples:\n"
        "- A futuristic cityscape at sunset\n"
        "- A cute robot playing chess\n"
        "- Underwater scene with bioluminescent creatures\n\n"
        "Get creative and let's generate some art! 🚀"
    )
    
    context.bot.send_message(chat_id=update.message.chat_id, text=welcome_message, parse_mode='Markdown')

def generate_image(update, context):
    """
    Generate an image with quality selection and sharing options
    """
    # Store the prompt in context for later use
    user_data['current_prompt'] = update.message.text

    # Create quality selection keyboard
    quality_keyboard = [
        [
            InlineKeyboardButton("🌱 Low Quality (512x384)", callback_data="quality_low"),
            InlineKeyboardButton("🌳 Medium Quality (768x576)", callback_data="quality_mid")
        ],
        [
            InlineKeyboardButton("🌲 High Quality (1024x768)", callback_data="quality_high")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(quality_keyboard)
    
    update.message.reply_text(
        "Select image quality for your prompt:", 
        reply_markup=reply_markup
    )

def quality_callback(update, context):
    """
    Handle quality selection and generate image
    """
    query = update.callback_query
    query.answer()
    
    # Extract quality from callback data
    quality = query.data.split('_')[1]
    prompt = user_data.get('current_prompt', 'A beautiful scene')

    # Send "generating" message
    loading_message = query.message.reply_text(
        f"🔄 Generating {quality.capitalize()} Quality Image... Please wait!"
    )

    try:
        # Generate image using Together AI with selected quality
        response = together_client.images.generate(
            prompt=prompt,
            **quality_params[quality]
        )

        # Decode base64 image
        image_data = base64.b64decode(response.data[0].b64_json)

        # Create sharing keyboard
        share_keyboard = [
            [
                InlineKeyboardButton("🐦 Share on Twitter", 
                    url=f"https://twitter.com/intent/tweet?text=Check%20out%20this%20AI-generated%20image!%20Created%20with%20@AIImageBot%20-%20Prompt:%20{prompt}"),
                InlineKeyboardButton("💼 Share on LinkedIn", 
                    url=f"https://www.linkedin.com/sharing/share-offsite/?url=&text=Check%20out%20this%20AI-generated%20image!%20Created%20with%20AI%20Image%20Generator%20-%20Prompt:%20{prompt}")
            ]
        ]
        share_markup = InlineKeyboardMarkup(share_keyboard)

        # Send the generated image with sharing options
        query.message.reply_photo(
            photo=image_data, 
            caption=f"🖼️ {quality.capitalize()} Quality Image\nPrompt: *{prompt}*",
            parse_mode='Markdown',
            reply_markup=share_markup
        )

    except Exception as e:
        # Handle errors
        error_message = (
            "❌ Oops! Something went wrong during image generation.\n"
            f"Error: {str(e)}\n\n"
            "Please try again with a different prompt."
        )
        query.message.reply_text(error_message)

    finally:
        # Delete loading message
        loading_message.delete()

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook handler to process Telegram updates
    """
    data = request.get_json()

    # Create Update object from incoming JSON
    update = Update.de_json(data, bot)

    # Create a dispatcher and handle the update
    dispatcher = Dispatcher(bot, None)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, generate_image))
    dispatcher.add_handler(CallbackQueryHandler(quality_callback, pattern=r'^quality_'))

    # Process the update
    dispatcher.process_update(update)

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Set webhook for Telegram
    webhook_url = os.getenv("WEBHOOK_URL")
    bot.set_webhook(url=webhook_url)

    app.run(debug=True, host='0.0.0.0', port=5000)
