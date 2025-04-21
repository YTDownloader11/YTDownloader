from concurrent.futures import ThreadPoolExecutor
import sys
import traceback

import tornado
import tornado.web
import tornado.gen
from tornado.ioloop import IOLoop
import asyncio

pool = ThreadPoolExecutor(max_workers=4)

class asyncRequestHandler(tornado.web.RequestHandler):
	"""
	Modern Tornado asynchronous request handler (Python 3.12+)
	Tornado asynchronous request handler
	create a class that extends this one (requestHelper.asyncRequestHandler)
	use asyncGet() and asyncPost() instead of get() and post().
	Done. I'm not kidding.
	"""

	async def get(self, *args, **kwargs):
		try:
			await run_background(self.asyncGet, *args, **kwargs)
		finally:
			if not self._finished:
				self.finish()

	async def post(self, *args, **kwargs):
		try:
			await run_background(self.asyncPost, *args, **kwargs)
		finally:
			if not self._finished:
				self.finish()

	def asyncGet(self, *args, **kwargs):
		self.send_error(405)

	def asyncPost(self, *args, **kwargs):
		self.send_error(405)

	def getRequestIP(self):
		"""
		Return CF-Connecting-IP (request IP when under cloudflare, you have to configure nginx to enable that)
		If that fails, return X-Forwarded-For (request IP when not under Cloudflare)
		if everything else fails, return remote IP

		:return: Client IP address
		"""
		headers = self.request.headers
		return (
			headers.get("X-Real-IP")
			or headers.get("CF-Connecting-IP")
			or headers.get("X-Forwarded-For")
			or self.request.remote_ip
		)

async def run_background(func, *args, **kwargs):
	"""
	Run a function in the background.
	Used to handle multiple requests at the same time

	:param data: (func, args, kwargs)
	:param callback: function to call when `func` (data[0]) returns
	:return:
	"""
	loop = asyncio.get_running_loop()
	return await loop.run_in_executor(pool, lambda: func(*args, **kwargs))

def checkArguments(arguments, requiredArguments):
	"""
	Check that every requiredArguments elements are in arguments

	:param arguments: full argument list, from tornado
	:param requiredArguments: required arguments list
	:return: True if all arguments are passed, False if not
	"""
	for i in requiredArguments:
		if i not in arguments:
			return False
	return True

def printArguments(t):
	"""
	Print passed arguments, for debug purposes

	:param t: tornado object (self)
	"""
	msg = "ARGS::"
	for i in t.request.arguments:
		msg += "{}={}\r\n".format(i, t.get_argument(i))
	print(msg)
