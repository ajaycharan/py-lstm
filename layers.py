## @package layers
# Definition of various supported layers

import numpy as np
import scipy.misc as scm
import copy
import utils

##
# The base class from which other layers will inherit. 
class BaseLayer(object):
	def __init__(self, **lPrms):
		#The layer parameters - these can
		#be different for different layers
		for n in lPrms:
			if hasattr(self,n):
				setattr(self,n,lPrms[n])
			else:
				raise Exception( "Attribute '%s' not found"%n )
		#The gradients wrt to the parameters and the bottom
		self.grad_ = {} 
		#Storing the weights and other stuff
		self.prms_ = {}
	
	@property
	def type(self):
		return type(self).__name__

	#Forward pass
	def forward(self, bottom, top):
		pass

	#Backward pass
	def backward(self, bottom, top, botgrad, topgrad):
		'''
			bottom : The inputs from the previous layer
			topgrad: The gradient from the next layer
			botgrad: The gradient to the bottom layer
		'''
		pass

	#Setup the layer including the top
	def setup(self, bottom, top):
		pass

	@property
	def gradient(self):
		'''
			Get the gradient of the parameters
		'''
		return self.grad_
	@property
	def flat_gradient(self):
		'''
			Get the gradient of the parameters as a 1d array
		'''
		return np.concatenate( [self.grad_[n].ravel() for n in sorted(self.grad_)], axis=0 )

	@property
	def flat_parameters(self):
		""" Fetch all the parameters of the layer and return them as a 1d array """
		if len(self.prms_) <= 0: return np.empty((0,))
		return np.concatenate( [self.prms_[n].ravel() for n in sorted(self.prms_)], axis=0 )
	@flat_parameters.setter
	def flat_parameters(self, value):
		""" Set all the parameters of the layer """
		k = 0
		for n in sorted(self.prms_):
			kk = k + self.prms_[n].size
			self.prms_[n].flat[...] = value[k:kk]
			k = kk
	
	@property
	def parameters(self):
		""" Return the layer parameters """
		return self.prms_

	def get_mutable_gradient(self, gradType):
		'''
			See get_gradient for the docs
		'''
		assert gradType in self.grad_.keys(), 'gradType: %s is not recognized' % gradType
		return copy.deepcopy(self.grad_[gradType])	

##
# Recitified Linear Unit (ReLU)
class ReLU(BaseLayer):
	def setup(self, bottom, top):
		for b,t in zip(bottom,top):
			t.resize(b.shape,refcheck=False)

	def forward(self, bottom, top):
		for b,t in zip(bottom,top):
			t[...] = np.maximum(b, 0)

	def backward(self, bottom, top, botgrad, topgrad):
		for b,t,db,dt in zip(bottom,top,botgrad,topgrad):
			db[...] = dt * (t>0)
	
##
# Sigmoid
class Sigmoid(BaseLayer):
	'''
		f(x) = 1/(1 + exp(-sigma * x))
	'''
	sigma = 1.0
	
	def setup(self, bottom, top):
		for b,t in zip(bottom,top):
			t.resize(b.shape,refcheck=False)
		
	def forward(self, bottom, top):
		for b,t in zip(bottom,top):
			# Numerically more stable
			d = -b * self.sigma
			ep = np.exp( -np.maximum(0,d) )
			en = np.exp( np.minimum(0,d) )
			t[...] = ep / (ep + en)

	def backward(self, bottom, top, botgrad, topgrad):
		for b,t,db,dt in zip(bottom,top,botgrad,topgrad):
			db[...] = dt * t * (1 - t) * self.sigma

##
#Inner Product
class InnerProduct(BaseLayer):
	'''
		The input and output will be batchSz * numUnits
	'''
	##TODO: Define weight fillers
	output_shape = 10
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		try: self.output_shape = tuple(self.output_shape)
		except: self.output_shape = (self.output_shape,)
	
	def setup(self, bottom, top):
		assert len(bottom) == 1 and len(top) == 1
		top[0].resize( self.output_shape, refcheck=False )
		# Initialize the parameters
		self.prms_['w'] = np.zeros(bottom[0].shape+self.output_shape,dtype=bottom[0].dtype)
		self.prms_['b'] = np.zeros(self.output_shape,dtype=bottom[0].dtype)
		self.grad_['w'] = np.zeros_like(self.prms_['w'])
		self.grad_['b'] = np.zeros_like(self.prms_['b'])

	def forward(self, bottom, top):
		# TODO: Make sure this is correct!
		top[0][...] = np.tensordot(bottom[0],  self.prms_['w']) + self.prms_['b'] 

	def backward(self, bottom, top, botgrad, topgrad):
		# TODO: Make sure this is correct! (use tensordot)
		#Gradients wrt to the inputs
		botgrad[0][...]  = np.dot(topgrad[0], np.transpose(self.grad_['w'])) 
		#Gradients wrt to the parameters
		self.grad_['w'][...] = np.dot(topgrad[0].transpose(), bottom[0]).transpose()
		self.grad_['b'][...] = np.sum(topgrad[0], axis=0)

##
#SoftMax
class SoftMax(BaseLayer):
	def setup(self, bottom, top):
		assert len(bottom) == 1 and len(top) == 1
		top[0].resize( bottom[0].output_shape, refcheck=False )
		
	def forward(self, bottom, top):
		# NOTE: Consider removing the num dimension for now!
		for i in range(bottom.shape[0]):
			# NOTE: Consider making this 1/Z exp(bottom) [no negation]
			mn = np.min(bottom[i,:])
			top[i, :] = np.exp(-(top[i,:] - mn))
			Z         = sum(top[i,:])
			top[i,:]  = top[i,:] / Z
	
	def backward(self, bottom, top, botgrad, topgrad):
		pass
