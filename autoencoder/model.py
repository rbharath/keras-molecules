
from keras import backend as K
from keras import objectives
from keras.models import Sequential, Model, load_model
from keras.layers import Input, Dense, Lambda
from keras.layers.core import Dense, Activation, Dropout, Flatten, Reshape, TimeDistributedDense, RepeatVector
from keras.layers.wrappers import TimeDistributed
from keras.layers.recurrent import LSTM, GRU
from keras.layers.embeddings import Embedding
from keras.layers.convolutional import Convolution1D, MaxPooling1D, ZeroPadding1D, UpSampling1D
from keras.layers.normalization import BatchNormalization
from keras.callbacks import TensorBoard
from keras.utils.visualize_util import plot, model_to_dot

class MoleculeVAE():

    autoencoder = None
    
    def create(self,
               charset,
               original_dim = 120,
               epsilon_std = 0.01,
               latent_rep_size = 292,
               weights_file = None):
        charset_length = len(charset)
        
        x = Input(shape=(original_dim, charset_length))
        h = Convolution1D(9, 9, input_dim=60)(x)
        h = Convolution1D(9, 9)(h)
        h = Convolution1D(10, 11)(h)
        h = Flatten()(h)
        h = Dense(435)(h)
        z_mean = Dense(latent_rep_size, name='z_mean')(h)
        z_log_var = Dense(latent_rep_size, name='z_log_var')(h)

        def sampling(args):
            z_mean, z_log_var = args
            batch_size = K.shape(z_mean)[0]
            epsilon = K.random_normal(shape=(batch_size, latent_rep_size), mean=0., std=epsilon_std)
            return z_mean + K.exp(z_log_var / 2) * epsilon

        z = Lambda(sampling)([z_mean, z_log_var])

        h = Dense(latent_rep_size, name='latent_input')(z)
        h = RepeatVector(original_dim)(h)
        h = GRU(501, return_sequences = True)(h)
        h = GRU(501, return_sequences = True)(h)
        h = GRU(501, return_sequences = True)(h)
        decoded_mean = TimeDistributedDense(charset_length, activation='softmax', name='decoded_mean')(h)

        def vae_loss(x, x_decoded_mean):
            x = K.flatten(x)
            x_decoded_mean = K.flatten(x_decoded_mean)
            xent_loss = original_dim * objectives.binary_crossentropy(x, x_decoded_mean)
            kl_loss = - 0.5 * K.mean(1 + z_log_var - K.square(z_mean) - K.exp(z_log_var), axis = -1)
            return xent_loss + kl_loss
        
        encoded_input = Input(shape=(original_dim, latent_rep_size))
        
        self.autoencoder = Model(x, decoded_mean)
        self.encoder = Model(x, z_mean)
        #self.decoder = Model(self.autoencoder.get_layer('latent_input')(encoded_input),
        #                     self.autoencoder.get_layer('decoded_mean')(encoded_input))
        
        if weights_file:
            self.autoencoder.load_weights(weights_file)
        
        self.autoencoder.compile(optimizer = 'Adam',
                                 loss = vae_loss,
                                 metrics = ['accuracy'])

    def save(self, filename):
        self.autoencoder.save_weights(filename)
    
    def load(self, charset, weights_file):
        self.create(charset, weights_file = weights_file)
