from tt.utils import notify, listener, BasePlugin
from tt.config import settings, logger
from talkytrend import TalkyTrend

class TalkyTrendPlugin(BasePlugin):
    def __init__(self):
        try:
            self.trend = TalkyTrend()
        except Exception as e:
            logger.warning(e)
    async def start(self):
        """Starts the TalkyTrend plugin"""
        try:
            while True:
                async for message in await self.trend.scanner():
                    await self.notify(message)
        except Exception as e:
            logger.warning(e)

    async def stop(self):
        """Stops the TalkyTrend plugin"""
        # Perform any necessary cleanup or shutdown tasks
        pass

    async def listen(self, message):
        """Listens for incoming messages or events"""
        # This plugin doesn't require listening for messages or events
        pass

    async def notify(self, message):
        """Sends a notification"""
        try:
            await notify(message)
        except Exception as e:
            logger.warning(e)
