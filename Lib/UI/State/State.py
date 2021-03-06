from tda import BaseExt


class State(BaseExt):
	"""
    TODO: Would using osc return values for things like active clip/deck reduce UI delay?
    """
	def __init__(self, ownerComponent, logger):
		super().__init__(ownerComponent, logger)
		self.oscOut = ownerComponent.op('oscout1')

		self.oscControlList = ownerComponent.op('opfind_oscControls')
		self.initializedControlList = ownerComponent.op('table_initializedControls')
		self.InitOSCControls()

		self.logInfo('UIState initialized')

	def InitOSCControls(self):
		"""
		TODO: call this on composition [re]load
		"""
		self.oscControlState = {}
		self.initializedControlList.clear()
		self.OnCtrlOPListChange()

	def SendMessage(self, address, *args):
		"""
		TODO: move this out of State and into OSC/Client?
		"""
		if address:
			self.logDebug('sending message to {}: {}'.format(address, args))
			self.oscOut.sendOSC(address, args)
		else:
			self.logWarning('attempted to send to invalid address {}'.format(address))

	def OnCtrlOPListChange(self):
		inactiveAddresses = set(self.oscControlState.keys())
		for row in self.oscControlList.rows()[1:]:
			[path, address] = [c.val for c in row]

			inactiveAddresses.discard(address)
			if address not in self.oscControlState:
				self.logDebug('initilizing ui state for {}'.format(address))
				self.oscControlState[address] = {'op': op(path)}
				self.SendMessage(address, '?')  # request initial value
				# NOTE: on receipt of initial value, address will be added to initializedControlList

		for inactiveAddress in inactiveAddresses:
			self.logDebug('clearing ui state for {}'.format(inactiveAddress))
			del self.oscControlState[inactiveAddress]
			if self.initializedControlList.row(inactiveAddress) is not None:
				self.initializedControlList.deleteRow(inactiveAddress)

	def OnOSCReply(self, address, *args):
		if address not in self.oscControlState:
			self.logWarning('recieved OSC reply for unkonwn address {}'.format(address))
			return

		if len(args) != 1:
			self.logWarning(
				'expected OSC reply to have exactly 1 arg but got {}, ignoring message'.
				format(len(args))
			)
			return

		self.logDebug('setting value of {} to {}'.format(address, args[0]))
		ctrlState = self.oscControlState[address]
		ctrlState['op'].par.Value0 = args[0]

		valueOutAddress = '{}/valueOut'.format(ctrlState['op'].path)
		opFamily = op(valueOutAddress).family  # CHOP, DAT, etc.

		self.initializedControlList.appendRow([address, valueOutAddress, opFamily])
