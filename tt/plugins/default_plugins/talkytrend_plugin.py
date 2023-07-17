import os
from tt.config import settings
from tt.utils import send_notification
from tt.plugins.plugin_manager import BasePlugin
from talkytrend import TalkyTrend

class TalkyTrendPlugin(BasePlugin):
    name = os.path.splitext(os.path.basename(__file__))[0]
    def __init__(self):
        self.enabled = settings.talkytrend_enabled
        if self.enabled:
            self.trend = TalkyTrend()

    async def start(self):
        """Starts the TalkyTrend plugin"""  
        # TODO create a scheduler 
        if self.enabled:
            while True:
                async for message in self.trend.scanner():
                    await self.send_notification(message)

    async def stop(self):
        """Stops the TalkyTrend plugin"""

    async def send_notification(self, message):
        """Sends a notification"""
        if self.enabled:
            await send_notification(message)

    def should_handle(self, message):
        """Returns plugin status"""
        return self.enabled

    async def handle_message(self, msg):
        """Handles incoming messages"""
        if not self.enabled:
            return
        if msg.startswith(settings.bot_ignore):
            return
        if msg.startswith(settings.bot_prefix):
            command, *args = msg.split(" ")
            command = command[1:]

            command_mapping = {
                settings.bot_command_help: self.trend.get_talkytrend_info,
                settings.bot_command_news: self.trend.get_tv,
                settings.bot_command_trend: self.trend.check_signal,
            }

            if command in command_mapping:
                function = command_mapping[command]
                await self.send_notification(f"{await function()}")