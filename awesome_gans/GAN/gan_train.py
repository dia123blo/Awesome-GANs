import time

import numpy as np
import tensorflow as tf

import awesome_gans.gan.gan_model as gan
import awesome_gans.image_utils as iu
from awesome_gans.datasets import MNISTDataSet as DataSet

results = {
    'output': './gen_img/',
    'model': './model/GAN-model.ckpt'
}

train_step = {
    'global_step': 200001,
    'logging_interval': 1000,
}


def main():
    start_time = time.time()  # Clocking start

    # MNIST Dataset load
    mnist = DataSet(ds_path="D:/DataSet/mnist/").data

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # GAN Model
        model = gan.GAN(s)

        # Initializing
        s.run(tf.global_variables_initializer())

        # Load model & Graph & Weights
        saved_global_step = 0
        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            model.saver.restore(s, ckpt.model_checkpoint_path)

            saved_global_step = int(ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1])
            print("[+] global step : %s" % saved_global_step, " successfully loaded")
        else:
            print('[-] No checkpoint file found')

        d_loss = 0.
        d_overpowered = False
        for global_step in range(saved_global_step, train_step['global_step']):
            batch_x, _ = mnist.train.next_batch(model.batch_size)
            batch_x = batch_x.reshape(-1, model.n_input)
            batch_z = np.random.uniform(-1., 1., size=[model.batch_size, model.z_dim]).astype(np.float32)

            # Update D network
            if not d_overpowered:
                _, d_loss = s.run([model.d_op, model.d_loss],
                                  feed_dict={
                                      model.x: batch_x,
                                      model.z: batch_z,
                                  })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.x: batch_x,
                                  model.z: batch_z,
                              })

            d_overpowered = d_loss < (g_loss / 2.)

            if global_step % train_step['logging_interval'] == 0:
                batch_x, _ = mnist.test.next_batch(model.batch_size)
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x: batch_x,
                                                    model.z: batch_z,
                                                })

                d_overpowered = d_loss < (g_loss / 2.)

                # Print loss
                print("[+] Step %08d => " % global_step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                samples = s.run(model.g,
                                feed_dict={
                                    model.z: sample_z,
                                })

                samples = np.reshape(samples, [-1, model.height, model.width, model.channel])

                # Summary saver
                model.writer.add_summary(summary, global_step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size
                sample_dir = results['output'] + 'train_{:08d}.png'.format(global_step)

                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir)

                # Model save
                model.saver.save(s, results['model'], global_step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))  # took about 370s on my machine

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
