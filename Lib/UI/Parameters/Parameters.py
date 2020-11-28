from tda import BaseExt
from tdaUtils import clearChildren, layoutComps


class ParameterContainer(BaseExt):
	@property
	def address(self):
		return self.ownerComponent.par.Address.eval()

	def __init__(self, ownerComponent, logger):
		super().__init__(ownerComponent, logger)
		self.sectionTemplate = op.uiTheme.op('sectionTemplate')
		self.parameterTemplates = {
			'Float': op.uiTheme.op('sliderHorzTemplate'),
			'Header': op.uiTheme.op('labelTemplate'),
			'StrMenu': op.uiTheme.op('dropDownMenuTemplate'),
			'Menu': op.uiTheme.op('dropDownMenuTemplate'),
			'Toggle': op.uiTheme.op('buttonRockerTemplate')
		}

		assert hasattr(
			ownerComponent.par, 'Address'
		), 'parameter containers must have an Address par'

		self.sectionContainer = self.ownerComponent.op('sections')
		assert self.sectionContainer, 'parameter containers must container a "sections" comp'

	def Init(self):
		self.sections = {}
		self.parameters = {}
		self.activeAddresses = set()
		clearChildren(self.sectionContainer)

		# # Create "root" section
		# # TODO: Change this based on container type
		# self.SyncSection(self.address, 'Layer')

		self.logInfo('initialized')

	def SyncSection(self, address, label):
		if address in self.sections:
			return

		self.logDebug('creating "{}" section for {}'.format(label, address))
		section = self.sectionContainer.copy(self.sectionTemplate, name=label)
		section.par.Label = label
		self.sections[address] = section
		layoutComps(self.sections.values(), columns=1)

		# TODO: request Sectionorder parameter over OSC return channel?

	def ResetActiveParameterList(self):
		self.activeAddresses = set()

	def getParameterSection(self, address):
		sectionAddress, _ = address.rsplit('/', 1)  # The last value is the parameter

		if sectionAddress not in self.sections:
			self.logDebug(f'section not found for {address}, initializing')
			_, label = sectionAddress.rsplit('/', 1)
			self.SyncSection(sectionAddress, label.title())

		return self.sections[sectionAddress]

	def SyncParameter(
		self, address, label, style, minValue, maxValue, menuLabels, order
	):  # pylint: disable=too-many-arguments
		if address in self.parameters:
			# if parameter in self.paths, do we need to do anything?
			#    will parameters change over time? Or only values?
			return

		if style == 'WH':
			self.logDebug(f'TODO: figure out what to do with WH parameters: {address}')
			return

		self.logDebug(f'creating parameter {address}')

		section = self.getParameterSection(address)
		sectionContents = section.op('sectionContents')

		assert style in self.parameterTemplates, f'no template defined for "{style}" parameters'
		parameter = sectionContents.copy(self.parameterTemplates[style], name=label)
		self.parameters[address] = parameter
		layoutComps(self.parameters.values(), columns=1)

		parameter.par.alignorder = order
		parameter.par.Widgetlabel = label

		if style == 'Header':
			return  # don't try and set parameters that don't exist

		parameter.par.Valname0 = address

		if style in ('StrMenu', 'Menu'):
			parameter.par.Menunames.expr = menuLabels
		elif style == 'Float':
			parameter.par.Value0.max = maxValue
			parameter.par.Value0.min = minValue


class Parameters(BaseExt):
	def __init__(self, ownerComponent, logger):
		super().__init__(ownerComponent, logger)
		self.parameterList = ownerComponent.op('null_parameterList')
		self.containerList = ownerComponent.op('null_containerList')
		self.containerState = {}

		self.OnParameterChange()
		self.logInfo('ParamatersUI initialized')

	def OnParameterChange(self):
		self.logDebug('parameter change detected')

		activeAddresses = set()
		lastMatchedParameter = 0
		for i in range(1, self.containerList.numRows):
			containerPath = str(self.containerList[i, 'path'])
			containerAddress = str(self.containerList[i, 'address'])
			nextAddress = str(self.containerList[i + 1, 'address'])

			container = self.syncContainerState(containerAddress, containerPath)
			# TODO: container.ResetActiveParameterState()
			activeAddresses.add(containerAddress)

			# group parameters into "containers" if par address starts
			# with the container address
			# NOTE: this assumes both lists are sorted by OSC address
			hasMatched = False
			for j in range(lastMatchedParameter + 1, self.parameterList.numRows):
				parAddress = str(self.parameterList[j, 'address'])
				if parAddress.startswith(containerAddress):
					container.SyncParameter(
						parAddress,
						label=str(self.parameterList[j, 'label']),
						style=str(self.parameterList[j, 'style']),
						minValue=str(self.parameterList[j, 'normmin']),
						maxValue=str(self.parameterList[j, 'normmax']),
						menuLabels=str(self.parameterList[j, 'menulabels']),
						order=str(self.parameterList[j, 'order']),
					)
					lastMatchedParameter = j
					hasMatched = True
				elif parAddress.startswith(nextAddress):
					# prevent re-checking unmatched pars on next iteration if we know there is a match
					lastMatchedParameter = j - 1
					break
				elif hasMatched:
					# We know that the rest won't since the lists are sorted
					break

			# TODO: container.clearInactiveParamaters

		inactiveAddresses = set(self.containerState.keys()) - activeAddresses
		for address in inactiveAddresses:
			self.logDebug('clearing parameter container state for {}'.format(address))
			del self.containerState[address]

	def syncContainerState(self, address: str, opPath: str) -> ParameterContainer:
		if address not in self.containerState:
			self.logDebug(
				'initializing parameter container state for {}'.format(address)
			)
			containerOP = op(opPath)
			containerOP.Init()
			self.containerState[address] = containerOP

		# TODO: Create collapsable container for layer parameters
		# TODO: fill layer paremeters into collapsable container
		# TODO: for each "effect", create collapsable container
		# TODO: for each parameter, insert into collapsable container

		return self.containerState[address]
