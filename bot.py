import os
import base64
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from together import Together
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ImageGenerationBot:
    def __init__(self, telegram_token: str, together_api_key: str):
        """
        Initialize the bot with enhanced image generation capabilities
        
        :param telegram_token: Telegram Bot API Token
        :param together_api_key: Together AI API Key
        """
        self.telegram_token = telegram_token
        self.together_client = Together(api_key=together_api_key)
        
        # Enhanced image generation parameters with quality options
        self.quality_params = {
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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Enhanced /start command with more detailed instructions
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
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def generate_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Generate an image with quality selection and sharing options
        """
        # Store the prompt in context for later use
        context.user_data['current_prompt'] = update.message.text
        
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
        
        await update.message.reply_text(
            "Select image quality for your prompt:", 
            reply_markup=reply_markup
        )

    async def quality_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle quality selection and generate image
        """
        query = update.callback_query
        await query.answer()
        
        # Extract quality from callback data
        quality = query.data.split('_')[1]
        prompt = context.user_data.get('current_prompt', 'A beautiful scene')
        
        # Send "generating" message
        loading_message = await query.message.reply_text(
            f"🔄 Generating {quality.capitalize()} Quality Image... Please wait!"
        )

        try:
            # Generate image using Together AI with selected quality
            response = self.together_client.images.generate(
                prompt=prompt,
                **self.quality_params[quality]
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
            await query.message.reply_photo(
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
            await query.message.reply_text(error_message)

        finally:
            # Delete loading message
            await loading_message.delete()

    def setup_handlers(self, application: Application):
        """
        Setup enhanced bot command and message handlers
        
        :param application: Telegram bot application
        """
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.generate_image
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                self.quality_callback, 
                pattern=r'^quality_'
            )
        )

def main():
    # Load environment variables
    load_dotenv()

    # Retrieve API credentials
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    together_api_key = os.getenv('TOGETHER_API_KEY')

    # Validate credentials
    if not telegram_token or not together_api_key:
        logger.error("Missing API credentials. Check your .env file.")
        return

    # Create bot application
    application = Application.builder().token(telegram_token).build()

    # Initialize and setup bot
    bot = ImageGenerationBot(telegram_token, together_api_key)
    bot.setup_handlers(application)

    # Start the bot
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
