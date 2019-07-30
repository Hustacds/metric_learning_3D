## -*- coding: utf-8 -*-


import numpy as np
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import torchvision.models as models
import cv2
from models.Model import Model
import torch.optim as optim
import random
from torch.utils.data import Dataset,DataLoader,TensorDataset
from ignite.engine import Engine, Events
from ignite.handlers import ModelCheckpoint, Timer
from ignite.metrics import RunningAverage















rootpath = 'D:\\GoodsRecognition\\FGR3D\\'



#加载特征数据
#
dataset_settings = ['1','2', '3','123_1', '123_2', '123_3','123_123']
# dataset_settings = ['123_1', '123_2', '123_3']
for dataset_setting in dataset_settings:

    fe_train_data = np.load(rootpath + 'dataset/fe_'+dataset_setting+'/fe_train.npz')
    fe_test_data = np.load(rootpath + 'dataset/fe_'+dataset_setting+'/fe_test.npz')

    fe_train = fe_train_data["fe_train"]
    labels_train = fe_train_data["labels_train"]

    fe_test = fe_test_data["fe_test"]
    labels_test = fe_test_data["labels_test"]

    # print(fe_train)
    # print(labels_train)

    # print(fe_test)
    # print(labels_test)

    #定义dataset和dataloader
    # 六组实验
    # 1. MVRNN + lose0        basic loss
    # 2. MVRNN + lose1        利用metric_learning 来引导feature
    # 3. MVCNN
    # 4. Mean
    # 5. Concatenate
    # 6. Multi retrieval
    # 7. Stack 再加卷积


    #以上8组实验，输入的数据都是一样的，比如随机选择多个视图，作为注册特征，然后其他的作为查询特征。
    #训练该怎么组织，测试又该怎么组织？
    #分类训练的测试样本，

    # 训练集 和测试集已经是分开了，
    #只有RNN是需要先分类的，其他几个都不用，所以不需要。分类的对比，只是在不同的loss时进行
    #  RNN应该也是做成端到端的才好，这样可以和其他几个网络统一

    # 3个数据集，每个数据集的视图数量不一样。那要怎么处理？如何保持样本的均衡？
    # 正样本，从每个物体里随机抽n张图，再从剩下的中间抽1张图作为一组样本，每个样本都是这样，
    # 负样本，从每个物体里随机抽n张图，再从其他物体中任意抽一张图，组成一组负样本

    for num_view in range(2,10,1):

        num_train_sample = 20000
        num_test_sample = 10000

        # num_train_sample = 200
        # num_test_sample = 100
        test_label_num = np.max(labels_test)
        train_label_num = np.max(labels_train)
        print(test_label_num)
        print(train_label_num)

        test_pos_require_feature = np.zeros((num_test_sample,512))                   #正样本检索特征
        test_pos_register_feature1 = np.zeros((num_test_sample,num_view,512))         #正样本注册特征
        test_pos_register_feature2 = np.zeros((num_test_sample,num_view,512))         #正样本注册特征
        test_neg_register_feature = np.zeros((num_test_sample,num_view,512))       #负样本注册特征

        list_index = np.random.choice(range(len(labels_test)),num_test_sample)        #根据样本下标

        for i in range(num_test_sample):
            sample_index = list_index[i]
            # print("第{}个样本label为{}".format(sample_index,labels_test[sample_index]))
            same_index = np.where(labels_test == labels_test[sample_index])[0]   #找到与第sample_index属于同一个物体的特征
            # print(same_index)
            same_index = np.append(np.arange(np.min(same_index),sample_index,1),np.arange(sample_index+1,np.max(same_index)+1,1))
            # print(same_index)
            pos_index1  = np.random.choice(same_index,num_view)
            # print(pos_index1)
            # print(labels_test[pos_index1])

            pos_index2 = np.random.choice(same_index, num_view)
            # print(pos_index2)
            # print(labels_test[pos_index2])

            diff_label = (labels_test[sample_index] + random.randint(1,test_label_num)) % (test_label_num+1)
            # print("负样本的label为{}".format(diff_label))
            diff_index = np.where(labels_test == diff_label )[0]
            # print(diff_index)
            neg_index =np.random.choice(diff_index,num_view)
            # print(neg_index)
            # print(labels_test[neg_index])
            test_pos_require_feature[i,:] = fe_test[sample_index]
            test_pos_register_feature1[i,:,:] = fe_test[pos_index1]
            test_pos_register_feature2[i, :, :] = fe_test[pos_index2]
            test_neg_register_feature[i, :, :] = fe_test[neg_index]

        # print(test_pos_require_feature)
        # print(test_pos_register_feature1)
        # print(test_pos_register_feature2)
        # print(test_neg_register_feature)

        test_pos_require_feature = torch.from_numpy(test_pos_require_feature).float()
        test_pos_register_feature1 = torch.from_numpy(test_pos_register_feature1).float()
        test_pos_register_feature2 = torch.from_numpy(test_pos_register_feature2).float()
        test_neg_register_feature = torch.from_numpy(test_neg_register_feature).float()

        test_dataset = TensorDataset(test_pos_require_feature,test_pos_register_feature1,test_pos_register_feature2,test_neg_register_feature)
        test_dataloader =DataLoader(dataset=test_dataset,batch_size=64,shuffle=False)

        # for i,data in enumerate(test_dataloader):
            # print('setp:{}'.format(i))
            # require_feature = data[0]
            # pos_feature1 = data[1]
            # pos_feature2 =  data[2]
            # neg_feature3 = data[3]

            # print(require_feature.shape)
            # print(pos_feature1.shape)
            # print(pos_feature2.shape)
            # print(neg_feature3.shape)



        train_pos_require_feature = np.zeros((num_train_sample,512))                   #正样本检索特征
        train_pos_register_feature1 = np.zeros((num_train_sample,num_view,512))         #正样本注册特征
        train_pos_register_feature2 = np.zeros((num_train_sample,num_view,512))         #正样本注册特征
        train_neg_register_feature = np.zeros((num_train_sample,num_view,512))       #负样本注册特征
        train_pos_label = np.ones(num_train_sample)
        train_neg_label = np.zeros(num_train_sample)

        list_index = np.random.choice(range(len(labels_train)),num_train_sample)        #根据样本下标

        for i in range(num_train_sample):
            sample_index = list_index[i]
            # print("第{}个样本label为{}".format(sample_index,labels_train[sample_index]))
            same_index = np.where(labels_train == labels_train[sample_index])[0]   #找到与第sample_index属于同一个物体的特征
            # print(same_index)
            same_index = np.append(np.arange(np.min(same_index),sample_index,1),np.arange(sample_index+1,np.max(same_index)+1,1))
            # print(same_index)
            pos_index1  = np.random.choice(same_index,num_view)
            # print(pos_index1)
            # print(labels_train[pos_index1])

            pos_index2 = np.random.choice(same_index, num_view)
            # print(pos_index2)
            # print(labels_train[pos_index2])

            diff_label = (labels_train[sample_index] + random.randint(1, train_label_num)) % (train_label_num+1)
            # print("负样本的label为{}".format(diff_label))
            diff_index = np.where(labels_train == diff_label )[0]
            # print(diff_index)
            neg_index =np.random.choice(diff_index,num_view)
            # print(neg_index)
            # print(labels_train[neg_index])
            train_pos_require_feature[i,:] = fe_train[sample_index]
            train_pos_register_feature1[i,:,:] = fe_train[pos_index1]
            train_pos_register_feature2[i, :, :] = fe_train[pos_index2]
            train_neg_register_feature[i, :, :] = fe_train[neg_index]

        # print(train_pos_require_feature)
        # print(train_pos_register_feature1)
        # print(train_pos_register_feature2)
        # print(train_neg_register_feature)

        train_pos_require_feature = torch.from_numpy(train_pos_require_feature).float()
        train_pos_register_feature1 = torch.from_numpy(train_pos_register_feature1).float()
        train_pos_register_feature2 = torch.from_numpy(train_pos_register_feature2).float()
        train_neg_register_feature = torch.from_numpy(train_neg_register_feature).float()
        train_pos_label = torch.from_numpy(train_pos_label).long()
        train_neg_label = torch.from_numpy(train_neg_label).long()

        train_dataset = TensorDataset(train_pos_require_feature,train_pos_register_feature1,train_pos_register_feature2,train_neg_register_feature,train_pos_label,train_neg_label)
        train_dataloader =DataLoader(dataset=train_dataset,batch_size=64,shuffle=True)

        # for i,data in enumerate(train_dataloader):
        #     print('setp:{}'.format(i))
        #     require_feature = data[0]
        #     pos_feature1 = data[1]
        #     pos_feature2 =  data[2]
        #     neg_feature3 = data[3]
        #
        #     print(require_feature.shape)
        #     print(pos_feature1.shape)
        #     print(pos_feature2.shape)
        #     print(neg_feature3.shape)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # 搭建RNN网络

        # typelist = ['rnn','rnn','maxpooling','averaging','concatenating','unfused','stack']
        # settings = ['exp1_mvrnn_basic', 'exp2_mvrnn_triplet', 'exp3_mvcnn', 'exp4_average', 'exp5_concatenate',
                    # 'exp6_unfused', 'exp7_stack']
        typelist = ['rnn','rnn','maxpooling','averaging','concatenating','unfused','stack']
        settings = ['exp1_mvrnn_basic', 'exp2_mvrnn_triplet', 'exp3_mvcnn', 'exp4_average', 'exp5_concatenate', 'exp6_unfused', 'exp7_stack']

        run_mode = True  #True 为训练，False为测试

        cross_loss = nn.CrossEntropyLoss()  #损失函数为交叉熵，多用于多分类问题
        triplet_loss = nn.TripletMarginLoss(margin=1.0,p=2)


        for i_test in range(len(typelist)):
            net_type = typelist[i_test]
            experiment = settings[i_test] +'_view' +str(num_view)
            print("开始测试第{}个实验{},设置为{}".format(i_test, net_type, experiment))

            log_path = rootpath + 'models/feature_match_'+dataset_setting+'/' + experiment



            if not os.path.exists(log_path):
                os.mkdir(log_path)
            else:
                files = os.listdir(log_path)
                for file in files:
                    os.remove(log_path +'/'+file)

            net = FFM(net_type,num_view)
            net = net.to(device)
            EPOCHS = 20
            # optimizer = optim.SSD(net.parameters(), lr=0.00001, momentum=0.9,
            #                       weight_decay=5e-4)
            optimizer = optim.Adam(net.parameters(), lr=0.0001,
                                  weight_decay=5e-4)  # 优化方式为mini-batch momentum-SGD，并采用L2正则化（权重衰减）
            best_acc = 0
            with open(log_path +"/acc.txt", "w") as f:
                with open(log_path +"/log.txt", "w")as f2:
                    for epoch in range(EPOCHS):
                        net.train()
                        if epoch ==10:
                            optimizer = optim.Adam(net.parameters(), lr=0.00001,
                                                  weight_decay=5e-4)  # 优化方式为mini-batch momentum-SGD，并采用L2正则化（权重衰减）
                        if epoch == 20:
                            optimizer = optim.Adam(net.parameters(), lr=0.000001,
                                                  weight_decay=5e-4)  # 优化方式为mini-batch momentum-SGD，并采用L2正则化（权重衰减）

                        print('\nEpoch: %d' % (epoch + 1))
                        sum_loss = 0.0
                        correct = 0.0
                        sum_pos = 0
                        acc_pos = 0
                        sum_neg = 0
                        acc_neg = 0

                        total = 0.0
                        for i,data in enumerate(train_dataloader):
                            length = len(train_dataloader)
                            require_feature = data[0].to(device)
                            pos_feature1 = data[1].to(device)
                            pos_feature2 = data[2].to(device)
                            neg_feature = data[3].to(device)
                            pos_label = data[4].to(device)
                            neg_label = data[5].to(device)
                            optimizer.zero_grad()

                            if not settings[i_test] == 'exp2_mvrnn_triplet':
                                pos_output_group1 = net(require_feature, pos_feature1)
                                # pos_feature1 = pos_output_group1[0]
                                pos_result1 = pos_output_group1[1]

                                neg_output_group = net(require_feature, neg_feature)
                                # neg_feature = neg_output_group[0]
                                neg_result = neg_output_group[1]

                                pos_labels = torch.ones(pos_result1.shape[0]).long().to(device)
                                neg_labels = torch.zeros(neg_result.shape[0]).long().to(device)

                                ratio = random.random()
                                if ratio >2.9:
                                    labels = torch.cat((pos_labels, pos_labels))
                                    result = torch.cat((pos_result1, pos_result1), 0).to(device)
                                else:
                                    labels = torch.cat((pos_labels,neg_labels))
                                    result = torch.cat((pos_result1,neg_result),0).to(device)

                                # print(pos_result1.shape)
                                # print(neg_result.shape)
                                # print(labels.shape)
                                # print(result.shape)

                                loss = cross_loss(result,labels)
                                # print(loss)

                            else:
                                pos_output_group1 = net(require_feature, pos_feature1)
                                pos_feature1 = pos_output_group1[0]
                                pos_result1 = pos_output_group1[1]

                                pos_output_group2 = net(require_feature, pos_feature2)
                                pos_feature2 = pos_output_group2[0]
                                pos_result2 = pos_output_group2[1]

                                neg_output_group = net(require_feature, neg_feature)
                                neg_feature = neg_output_group[0]
                                neg_result = neg_output_group[1]

                                pos_labels = torch.ones(pos_result1.shape[0]).long().to(device)
                                neg_labels = torch.zeros(neg_result.shape[0]).long().to(device)


                                if ratio >2:
                                    labels = torch.cat((neg_labels, neg_labels))
                                    result = torch.cat((neg_result, neg_result), 0).to(device)
                                else:
                                    labels = torch.cat((pos_labels,neg_labels))
                                    result = torch.cat((pos_result1,neg_result),0).to(device)

                                # print(cross_loss(result, labels))
                                # print(triplet_loss(pos_feature1,pos_feature2,neg_feature))
                                loss = cross_loss(result, labels) + triplet_loss(pos_feature1,pos_feature2,neg_feature)
                                # print(loss)


                            loss.backward()
                            optimizer.step()
                            sum_loss +=loss.item()

                            _, neg_predicted = torch.max(neg_result.data, 1)
                            _, pos_predicted = torch.max(pos_result1.data, 1)

                            acc_pos += pos_predicted.eq(pos_labels.data).cpu().sum()
                            sum_pos += pos_result1.shape[0]
                            acc_neg += neg_predicted.eq(neg_labels.data).cpu().sum()
                            sum_neg += neg_result.shape[0]

                            str_log = '[epoch:{}, iter:{}] Loss: {:.4f} | acc_neg: {:10d} ,acc_pos: {:10d}, {:10d} |  Acc: {:.3f}%   | Neg_Acc: {:.3f}% | Pos_Acc: {:.3f}%'.format(epoch+1,(i+1+epoch*length),sum_loss/(i+1),acc_neg,acc_pos,sum_pos, 100.0*float(acc_pos+acc_neg)/float(sum_neg + sum_pos),100.0 * float(acc_neg) / float(sum_neg), 100.0 * float(acc_pos) / float(sum_pos) )

                            print(str_log)
                            f2.write(str_log)

                            # print('[epoch:%d, iter:%d] Loss: %.03f | %d ,%d  |  Acc: %.3f %%    | Neg_Acc: %.3f %% | Pos_Acc: %.3f %% '
                            #       % (epoch + 1, (i + 1 + epoch * length), sum_loss / (i + 1), acc_pos ,acc_neg ,100.0*(acc_pos+acc_neg)/(sum_neg + sum_pos),100.0 * acc_neg / sum_neg, 100.0 * acc_pos / sum_pos ))
                            # f2.write('%03d  %05d |Loss: %.03f |   %d ,%d   |  Acc: %.3f %% | Neg_Acc: %.3f %%  |  Pos_Acc: %.3f %% '
                            #          % (epoch + 1, (i + 1 + epoch * length), sum_loss / (i + 1), acc_pos ,acc_neg , 100.0*(acc_pos+acc_neg)/(sum_neg + sum_pos), 100.0 * acc_neg / sum_neg, 100.0 * acc_pos / sum_pos
                            #             ))
                            f2.write('\n')
                            f2.flush()
                        print("Wainting Test!")
                        with torch.no_grad():
                            acc_neg = 0
                            sum_neg = 0
                            acc_pos = 0
                            sum_pos = 0
                            net.eval()
                            for i,data in enumerate(test_dataloader):
                                require_feature = data[0].to(device)
                                pos_feature1 = data[1].to(device)
                                pos_feature2 = data[2].to(device)
                                neg_feature = data[3].to(device)


                                pos_output_group1 = net(require_feature, pos_feature1)
                                # pos_feature1 = pos_output_group1[0]
                                pos_result1 = pos_output_group1[1]

                                neg_output_group = net(require_feature, neg_feature)
                                # neg_feature = neg_output_group[0]
                                neg_result = neg_output_group[1]

                                pos_labels = torch.ones(pos_result1.shape[0]).long().to(device)
                                neg_labels = torch.zeros(neg_result.shape[0]).long().to(device)

                                # labels = torch.cat((pos_labels, neg_labels))
                                # result = torch.cat((pos_result1, neg_result), 0).to(device)

                                _, neg_predicted = torch.max(neg_result.data, 1)
                                _, pos_predicted = torch.max(pos_result1.data, 1)
                                # print(neg_labels.shape)
                                # print(neg_predicted.shape)
                                acc_pos += pos_predicted.eq(pos_labels.data).cpu().sum()
                                sum_pos += pos_result1.shape[0]
                                acc_neg += neg_predicted.eq(neg_labels.data).cpu().sum()
                                sum_neg += neg_result.shape[0]

                            str_test_log = '测试分类准确率为：[epoch:{}]| acc_neg: {:10d} ,acc_pos: {:10d}, {:10d} |  Acc: {:.3f}%   | Neg_Acc: {:.3f}% | Pos_Acc: {:.3f}%'.format(epoch+1,acc_neg,acc_pos,sum_pos, 100.0*float(acc_pos+acc_neg)/float(sum_neg + sum_pos),100.0 * float(acc_neg) / float(sum_neg), 100.0 * float(acc_pos) / float(sum_pos) )
                            print(str_test_log)
                            # print('测试分类准确率为：%.3f%%, %.3f%%, %.3f%%' % (100.0 * (acc_neg+acc_pos) / (sum_neg+sum_pos), 100.0 * acc_neg / sum_neg,100.0* acc_pos/sum_pos))
                            acc = 100. *  (acc_neg+acc_pos) / (sum_neg+sum_pos)
                            # 将每次测试结果实时写入acc.txt文件中
                            print('Saving model......')
                            torch.save(net.state_dict(),
                                       '%s/net_%03d.pth' % (log_path , epoch + 1))
                            # f.write("EPOCH=%03d,Accuracy= %.3f%%, neg_acc =  %.3f%%, pos_acc =  %.3f%%" % (epoch + 1, acc, 100.0 * float(acc_neg) / float(sum_neg),100.0* float(acc_pos)/float(sum_pos)))
                            f.write(str_test_log)
                            f.write('\n')
                            f.flush()
                            # 记录最佳测试分类准确率并写入best_acc.txt文件中
                            if acc > best_acc:
                                f3 = open(log_path+"/best_acc.txt", "w")
                                f3.write('EPOCH={:10d},best_acc= {:.3f}%'.format(epoch+1,100. *  float(acc_neg+acc_pos) / float(sum_neg+sum_pos)))
                                # f3.write("EPOCH=%d,best_acc= %.3f%%" % (epoch + 1, acc))
                                f3.close()
                                best_acc = acc

import argparse
import os
import sys
import torch

from torch.backends import cudnn
sys.path.append('.')
from config import cfg

from utils.logger import setup_logger

def main():
    parser = argparse.ArgumentParser(description="ReID Baseline Training")
    parser.add_argument(
        "--config_file", default="", help="path to config file", type=str
    )
    parser.add_argument("opts", help="Modify config options using the command-line", default=None,
                        nargs=argparse.REMAINDER)

    args = parser.parse_args()

    num_gpus = int(os.environ["WORLD_SIZE"]) if "WORLD_SIZE" in os.environ else 1

    if args.config_file != "":
        cfg.merge_from_file(args.config_file)
    cfg.merge_from_list(args.opts)
    cfg.freeze()

    output_dir = cfg.OUTPUT_DIR
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    logger = setup_logger("metric_learning_3D", output_dir, 0)
    logger.info("Using {} GPUS".format(num_gpus))
    logger.info(args)

    if args.config_file != "":
        logger.info("Loaded configuration file {}".format(args.config_file))
        with open(args.config_file, 'r') as cf:
            config_str = "\n" + cf.read()
            logger.info(config_str)
    logger.info("Running with config:\n{}".format(cfg))

    if cfg.MODEL.DEVICE == "cuda":
        os.environ['CUDA_VISIBLE_DEVICES'] = cfg.MODEL.DEVICE_ID    # new add by gu
    cudnn.benchmark = True
    train(cfg)

if __name__ == '__main__':
    main()