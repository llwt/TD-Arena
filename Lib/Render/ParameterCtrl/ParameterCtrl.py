from tda import LoadableExt


def getParValue(parameter):
	if parameter is None:
		return None

	if parameter.isMenu:
		return parameter.menuIndex

	return parameter.eval()


DEFAULT_STATE = {}


class ParameterCtrl(LoadableExt):
	def __init__(self, ownerComponent, logger, oscDispatcher):
		super().__init__(ownerComponent, logger)

		self.oscDispatcher = oscDispatcher
		self.parameterState = ownerComponent.op('null_internalParameterState')
		self.initializedParameterTable = ownerComponent.op(
			'table_initializedParameters'
		)

	def Init(self):
		self.setUnloaded()

		self.initializedParameterTable.clear()
		self.saveState = None

		self.logInfo('initialized')

	def Load(self, saveState=None):
		self.setLoading()
		self.logInfo('loading parameters')

		# Rather than load the parameter state immediately, we load it on-demand
		# as parameters are created (see OnParameterStateChange). Otherwise it
		# would be a bit messy to manage things like toxes that are asynchronusly
		# initialized.
		self.saveState = saveState or DEFAULT_STATE

		self.logInfo('loaded {} parameters into composition'.format(0))
		self.setLoaded()

	def GetSaveState(self):
		return {
			address.val: getParValue(self.getParameter(address.val))
			for address in self.parameterState.col('address')[1:]
		}

	def ReplyWithCurrentValue(self, address, _):
		par = self.getParameter(address)
		if par is None:
			self.logError(f'could not find parameter value for {address}')
			return

		self.logDebug('replying with current value at {}'.format(address))
		self.oscDispatcher.Reply(address, getParValue(par))

	def getParameter(self, address: str):
		controlPathCell = self.parameterState[address, 'path']
		parNameCell = self.parameterState[address, 'name']
		if controlPathCell is None or parNameCell is None:
			self.logWarning(f'could not find parameter state for {address}')
			return None

		controlOp = op(controlPathCell.val)
		if controlOp is None:
			self.logWarning(
				f'could not lookup current value for non-existent op {controlPathCell}'
			)
			return None

		par = controlOp.par[parNameCell.val]
		if par is None:
			self.logWarning(
				f'requested par {parNameCell} does not exist on {controlPathCell}'
			)

		return par

	def initializeParameter(self, address: str):
		assert hasattr(
			self, 'saveState'
		), 'parameters cannot be initialized before save state is loaded'

		if address not in self.saveState:
			return

		# NOTE: we remove values from saveState as they are requested
		#       to avoid initializing with a previous save value if a
		# 		parameter with the same address is created in the
		#       future
		saveValue = self.saveState.pop(address)
		par = self.getParameter(address)

		if par is None:
			self.logWarning(
				f'attempted to initialize parameter that doesn\'t exist @ {address}'
			)
			return

		par.val = saveValue

	def OnParameterStateChange(self):
		initializedAddresses = {
			row[0].val
			for row in self.initializedParameterTable.rows()
		}

		for i, _ in enumerate(self.parameterState.rows()[1:], 1):
			address = self.parameterState[i, 'address'].val
			if address not in initializedAddresses:
				self.initializeParameter(address)
				self.initializedParameterTable.appendRow([address])
			else:
				initializedAddresses.discard(address)

		# Clear out addresses that no longer correspond to parameters (e.g. from clearing a clip)
		for inactiveAddress in initializedAddresses:
			self.initializedParameterTable.deleteRow(inactiveAddress)
