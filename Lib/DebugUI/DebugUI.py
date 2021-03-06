class DebugUI:
	@property
	def IsOpen(self):
		return self.windowInfo['winopen']

	def __init__(self, ownerComp) -> None:
		self.ownerComp = ownerComp
		self.window = ownerComp.op('window_debug')
		self.windowInfo = ownerComp.op('info_window')

	def Open(self):
		if not self.IsOpen:
			self.window.par.winopen.pulse()
