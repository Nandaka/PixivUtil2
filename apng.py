#! python3

u"""This is an APNG module, which can create apng file from pngs

Reference:
http://littlesvr.ca/apng/
http://wiki.mozilla.org/APNG_Specification
https://www.w3.org/TR/PNG/
"""

from __future__ import with_statement
from __future__ import absolute_import
import struct
import binascii
import itertools
import io
from io import open

__version__ = u"0.1.0"

try:
	import PIL.Image
except ImportError:
	# Without Pillow, apng can only handle PNG images
	pass

PNG_SIGN = "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"

def is_png(png):
	u"""Test if @png is valid png file by checking signature

	@png can be str of the filename, a file-like object, or a bytes object.
	"""
	if isinstance(png, unicode):
		with open(png, u"rb") as f:
			png = f.read(8)

	if hasattr(png, u"read"):
		png = png.read(8)

	return png[:8] == PNG_SIGN

def chunks_read(b):
	u"""Parse PNG bytes into different chunks, yielding (type, data).

	@type is a string of chunk type.
	@data is the bytes of the chunk. Including length, type, data, and crc.
	"""
	# skip signature
	i = 8
	# yield chunks
	while i < len(b):
		data_len, = struct.unpack(u"!I", b[i:i+4])
		type = b[i+4:i+8].decode(u"latin-1")
		yield type, b[i:i+data_len+12]
		i += data_len + 12

def chunks(png):
	u"""Yield chunks from png.

	@png can be a string of filename, a file-like object, or a bytes bject.
	"""
	if not is_png(png):
		# convert to png
		if isinstance(png, str):
			with io.BytesIO(png) as f:
				with io.BytesIO() as f2:
					PIL.Image.open(f).save(f2, u"PNG", optimize=True)
					png = f2.getvalue()
		else:
			with io.BytesIO() as f2:
				PIL.Image.open(png).save(f2, u"PNG", optimize=True)
				png = f2.getvalue()

	if isinstance(png, unicode):
		# file name
		with open(png, u"rb") as f:
			png = f.read()

	if hasattr(png, u"read"):
		# file like
		png = png.read()

	return chunks_read(png)

def make_chunk(type, data):
	u"""Create chunk with @type and chunk data @data.

	It will calculate length and crc for you. Return bytes.

	@type is str and @data is bytes.
	"""
	out = struct.pack(u"!I", len(data))
	data = type.encode(u"latin-1") + data
	crc32 = binascii.crc32(data)
	out += data + struct.pack(u"!i", crc32)
	return out

class PNG(object):
	u"""Construct PNG image"""
	def __init__(self):
		self.hdr = None
		self.end = None
		self.width = None
		self.height = None
		self.chunks = []

	def init(self):
		u"""Extract some info from chunks"""
		for type, data in self.chunks:
			if type == u"IHDR":
				self.hdr = data
			elif type == u"IEND":
				self.end = data

		if self.hdr:
			# grab w, h info
			self.width, self.height = struct.unpack(u"!II", self.hdr[8:16])

	@classmethod
	def open(cls, file):
		u"""Open a png from file. See chunks()."""
		o = cls()
		o.chunks = list(chunks(file))
		o.init()
		return o

	@classmethod
	def from_chunks(cls, chunks):
		u"""Construct PNG from chunks.

		@chunks is a list of (type, data) tuple. See chunks().
		"""
		o = cls()
		o.chunks = chunks
		o.init()
		return o

	def to_bytes(self):
		u"""Get bytes"""
		chunks = [PNG_SIGN]
		chunks.extend(c[1] for c in self.chunks)
		return "".join(chunks)

	def save(self, file):
		u"""Save to file. @file can be a str of filename or a file-like object.
		"""
		if isinstance(file, unicode):
			with open(file, u"wb") as f:
				f.write(self.to_bytes())
		else:
			file.write(self.to_bytes())

class FrameControl(object):
	u"""Construct fcTL info"""
	def __init__(self, width=None, height=None, x_offset=0, y_offset=0, delay=100, delay_den=1000, depose_op=1, blend_op=0):
		self.width = width
		self.height = height
		self.x_offset = x_offset
		self.y_offset = y_offset
		self.delay = delay
		self.delay_den = delay_den
		self.depose_op = depose_op
		self.blend_op = blend_op

	def to_bytes(self):
		u"""Return bytes"""
		return struct.pack(u"!IIIIHHbb", self.width, self.height, self.x_offset, self.y_offset, self.delay, self.delay_den, self.depose_op, self.blend_op)

	@classmethod
	def from_bytes(cls, b):
		u"""Contruct fcTL info from bytes.

		@b should be a 28 length bytes object, excluding sequence number and crc.
		"""
		return cls(*struct.unpack(u"!IIIIHHbb", b))

class APNG(object):
	u"""Construct APNG image"""
	def __init__(self):
		self.frames = []

	def append(self, png, **options):
		u"""Append one frame.

		@png      See PNG.open.
		@options  See FrameControl.
		"""
		png = PNG.open(png)
		control = FrameControl(**options)
		if control.width is None:
			control.width = png.width
		if control.height is None:
			control.height = png.height
		self.frames.append((png, control))

	def to_bytes(self):
		u"""Return binary."""

		# grab the chunks we needs
		out = [PNG_SIGN]
		seq = 0

		# for first frame
		png, control = self.frames[0]

		# header
		out.append(png.hdr)

		# acTL
		out.append(make_chunk(u"acTL", struct.pack(u"!II", len(self.frames), 0)))

		# tRNS.
		# FIXME: HoneyView need this chunk to render animation, but why?
		# HoneyView 5.16 #4750, 2016/02/05
		out.append(make_chunk(u"tRNS", str(6)))

		# fcTL
		if control:
			out.append(make_chunk(u"fcTL", struct.pack(u"!I", seq) + control.to_bytes()))
			seq += 1

		# and others...
		for type, data in png.chunks:
			if type in (u"IHDR", u"IEND"):
				continue
			out.append(data)

		# FIXME: we should do some optimization to frames...
		# for other frames
		for png, control in self.frames[1:]:
			# fcTL
			out.append(
				make_chunk(u"fcTL", struct.pack(u"!I", seq) + control.to_bytes())
			)
			seq += 1

			# and others...
			for type, data in png.chunks:
				if type in (u"IHDR", u"IEND"):
					continue

				# convert IDAT to fdAT
				if type == u"IDAT":
					out.append(
						make_chunk(u"fdAT", struct.pack(u"!I", seq) + data[8:-4])
					)
					seq += 1
				else:
					out.append(data)

		# end
		out.append(png.end)

		return "".join(out)

	@classmethod
	def from_files(cls, files, **options):
		u"""Create APNG instance from multiple files.

		You can convert a series of image into apng by:
		  APNG.from_files(files, delay=100).save(out_file_name)

		Note that if you want to use different delays between each frames, you
		have to use APNG.append separately to construct different frame
		control.

		See APNG.append for valid params.
		"""
		o = cls()
		for file in files:
			o.append(file, **options)
		return o

	@classmethod
	def open(cls, file):
		u"""Open a apng file.

		@file can be a str of filename, a file-like object, or a bytes object.
		"""
		hdr = None
		end = (u"IEND", make_chunk(u"IEND", ""))

		frame_chunks = []
		frames = []

		control = None

		for type, data in PNG.open(file).chunks:
			if type == u"IHDR":
				hdr = data
				frame_chunks.append((type, data))
			elif type == u"acTL":
				continue
			elif type == u"fcTL":
				if any(c[0] == u"IDAT" for c in frame_chunks):
					# IDAT inside chunk
					frame_chunks.append(end)
					frames.append((PNG.from_chunks(frame_chunks), control))

					control = FrameControl.from_bytes(data[12:-4])
					hdr = make_chunk(u"IHDR", struct.pack(u"!II", control.width, control.height) + hdr[16:-4])
					frame_chunks = [(u"IHDR", hdr)]
				else:
					control = FrameControl.from_bytes(data[12:-4])
			elif type == u"fdAT":
				# convert to IDAT
				frame_chunks.append((u"IDAT", make_chunk(u"IDAT", data[12:-4])))
			elif type == u"IEND":
				# end
				frame_chunks.append(end)
				frames.append((PNG.from_chunks(frame_chunks), control))
				break
			else:
				frame_chunks.append((type, data))

		o = cls()
		o.frames = frames
		return o

	def save(self, file):
		u"""Save to file. @file can be a str of filename or a file-like object.
		"""
		if isinstance(file, unicode) or isinstance(file, str):
			with open(file, u"wb") as f:
				f.write(self.to_bytes())
		else:
			file.write(self.to_bytes())
