import tensorflow as tf


class DeepQModel:
    def __init__(self, input_size=2608, output_size=4):
        self.input_size = input_size
        self.output_size = output_size
        self.learning_rate = 1e-4
        self.input = tf.placeholder(shape=[1, input_size], dtype=tf.float32)

        self.qVal = self.forward_pass()
        self.nextQ = tf.placeholder(shape=[1, output_size], dtype=tf.float32)
        self.loss = self.loss_function()
        self.optimizer = self.optimizer_function()

    def forward_pass(self):
        """
        Predicts a action given an game state using fully connected layers

        :return: the predicted label as a tensor
        """
        w1 = tf.Variable(tf.zeros([self.input_size, self.input_size * 10]))
        b1 = tf.Variable(tf.zeros([self.input_size * 10]))
        o1 = tf.nn.relu(tf.add(tf.matmul(self.input, w1), b1))

        w2 = tf.Variable(tf.zeros([self.input_size * 10, self.output_size]))
        b2 = tf.Variable(tf.zeros([self.output_size],))
        o2 = tf.nn.sigmoid(tf.add(tf.matmul(o1, w2), b2))

        return o2

    def loss_function(self):
        return tf.reduce_sum(tf.square(self.nextQ - self.qVal))

    def optimizer_function(self):
        # return tf.train.GradientDescentOptimizer(learning_rate=self.learning_rate).minimize(self.loss)
        return tf.train.AdamOptimizer(learning_rate=self.learning_rate).minimize(self.loss)
