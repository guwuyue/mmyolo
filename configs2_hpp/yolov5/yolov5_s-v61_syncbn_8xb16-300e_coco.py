_base_ = '../_base_/default_runtime.py'

# dataset settings
data_root = 'data/coco/'
dataset_type = 'YOLOv5CocoDataset'

# parameters that often need to be modified
num_classes = 80
img_scale = (640, 640)  # width, height
deepen_factor = 0.33  # 控制网络结构深度的缩放因子，YOLOv5-s 为 0.33
widen_factor = 0.5  # 控制网络结构宽度的缩放因子，YOLOv5-s 为 0.5
max_epochs = 300  # 最大训练轮次 300 轮
save_epoch_intervals = 10  # 验证间隔，每 10 个 epoch 验证一次
train_batch_size_per_gpu = 16  # 训练时单个 GPU 的 Batch size
train_num_workers = 8  # 训练时单个 GPU 分配的数据加载线程数
val_batch_size_per_gpu = 1  # 验证时单个 GPU 的 Batch size
val_num_workers = 2  # 验证时单个 GPU 分配的数据加载线程数

# persistent_workers must be False if num_workers is 0.
persistent_workers = True

# Base learning rate for optim_wrapper
base_lr = 0.01

# only on Val
batch_shapes_cfg = dict(
    type='BatchShapePolicy',
    batch_size=val_batch_size_per_gpu,
    img_size=img_scale[0],
    size_divisor=32,
    extra_pad_ratio=0.5)

anchors = [ # 多尺度的先验框基本尺寸
    [(10, 13), (16, 30), (33, 23)],  # P3/8
    [(30, 61), (62, 45), (59, 119)],  # P4/16
    [(116, 90), (156, 198), (373, 326)]  # P5/32
]
strides = [8, 16, 32]  # 先验框生成器的步幅
num_det_layers = 3

# single-scale training is recommended to
# be turned on, which can speed up training.
env_cfg = dict(cudnn_benchmark=True)

model = dict(
    type='YOLODetector',  # 检测器名
    data_preprocessor=dict(  # 数据预处理器的配置，通常包括图像归一化和 padding
        type='mmdet.DetDataPreprocessor',  # 数据预处理器的类型，还可以选择 'YOLOv5DetDataPreprocessor' 训练速度更快
        mean=[0., 0., 0.],  # 用于预训练骨干网络的图像归一化通道均值，按 R、G、B 排序
        std=[255., 255., 255.],  # 用于预训练骨干网络的图像归一化通道标准差，按 R、G、B 排序
        bgr_to_rgb=True),  # 是否将图像通道从 BGR 转为 RGB
    backbone=dict(   # 主干网络的配置文件
        type='YOLOv5CSPDarknet',  # 主干网络的类别，目前可选用 'YOLOv5CSPDarknet', 'YOLOv6EfficientRep', 'YOLOXCSPDarknet' 3种
        deepen_factor=deepen_factor,  # 控制网络结构深度的缩放因子
        widen_factor=widen_factor,  # 控制网络结构宽度的缩放因子
        norm_cfg=dict(type='BN', momentum=0.03, eps=0.001),  # 归一化层(norm layer)的配置项
        act_cfg=dict(type='SiLU', inplace=True)),  # 激活函数(activation function)的配置项
    neck=dict(
        type='YOLOv5PAFPN',  # 检测器的 neck 是 YOLOv5FPN，我们同样支持 'YOLOv6RepPAFPN', 'YOLOXPAFPN'
        deepen_factor=deepen_factor,  # 控制网络结构深度的缩放因子
        widen_factor=widen_factor,  # 控制网络结构宽度的缩放因子
        in_channels=[256, 512, 1024],  # 输入通道数，与 Backbone 的输出通道一致
        out_channels=[256, 512, 1024],  # 输出通道数，与 Head 的输入通道一致
        num_csp_blocks=3,  # CSPLayer 中 bottlenecks 的数量
        norm_cfg=dict(type='BN', momentum=0.03, eps=0.001),  # 归一化层(norm layer)的配置项
        act_cfg=dict(type='SiLU', inplace=True)),  # 激活函数(activation function)的配置项
    bbox_head=dict(
        type='YOLOv5Head',  # bbox_head 的类型是 'YOLOv5Head', 我们目前也支持 'YOLOv6Head', 'YOLOXHead'
        head_module=dict(
            type='YOLOv5HeadModule',  # head_module 的类型是 'YOLOv5HeadModule', 我们目前也支持 'YOLOv6HeadModule', 'YOLOXHeadModule'
            num_classes=num_classes,  # 分类的类别数量
            in_channels=[256, 512, 1024],  # 输入通道数，与 Neck 的输出通道一致
            widen_factor=widen_factor,  # 控制网络结构宽度的缩放因子
            featmap_strides=strides,  # 多尺度特征图的步幅
            num_base_priors=3),  # 在一个点上，先验框的数量
        prior_generator=dict(  # 先验框(prior)生成器的配置
            type='mmdet.YOLOAnchorGenerator',  # 先验框生成器的类型是 mmdet 中的 'YOLOAnchorGenerator'
            base_sizes=anchors,  # 多尺度的先验框基本尺寸
            strides=strides),  # 先验框生成器的步幅, 与 FPN 特征步幅一致。如果未设置 base_sizes，则当前步幅值将被视为 base_sizes。
        # scaled based on number of detection layers
        loss_cls=dict(
            type='mmdet.CrossEntropyLoss',
            use_sigmoid=True,
            reduction='mean',
            loss_weight=0.5 * (num_classes / 80 * 3 / num_det_layers)),
        loss_bbox=dict(
            type='IoULoss',
            iou_mode='ciou',
            bbox_format='xywh',
            eps=1e-7,
            reduction='mean',
            loss_weight=0.05 * (3 / num_det_layers),
            return_iou=True),
        loss_obj=dict(
            type='mmdet.CrossEntropyLoss',
            use_sigmoid=True,
            reduction='mean',
            loss_weight=1.0 * ((img_scale[0] / 640)**2 * 3 / num_det_layers)),
        prior_match_thr=4.,
        obj_level_weights=[4., 1., 0.4]),
    test_cfg=dict(
        multi_label=True,   # 对于多类别预测来说是否考虑多标签，默认设置为 True
        nms_pre=30000,  # NMS 前保留的最大检测框数目
        score_thr=0.001,  # 过滤类别的分值，低于 score_thr 的检测框当做背景处理
        nms=dict(type='nms', iou_threshold=0.65),  # NMS 的类型  NMS 的阈值
        max_per_img=300))  # 每张图像 NMS 后保留的最大检测框数目

albu_train_transforms = [
    dict(type='Blur', p=0.01),
    dict(type='MedianBlur', p=0.01),
    dict(type='ToGray', p=0.01),
    dict(type='CLAHE', p=0.01)
]

pre_transform = [
    dict(type='LoadImageFromFile', file_client_args=_base_.file_client_args),
    dict(type='LoadAnnotations', with_bbox=True)
]

train_pipeline = [
    *pre_transform,
    dict(
        type='Mosaic',
        img_scale=img_scale,
        pad_val=114.0,
        pre_transform=pre_transform),
    dict(
        type='YOLOv5RandomAffine',
        max_rotate_degree=0.0,
        max_shear_degree=0.0,
        scaling_ratio_range=(0.5, 1.5),
        # img_scale is (width, height)
        border=(-img_scale[0] // 2, -img_scale[1] // 2),
        border_val=(114, 114, 114)),
    dict(
        type='mmdet.Albu',
        transforms=albu_train_transforms,
        bbox_params=dict(
            type='BboxParams',
            format='pascal_voc',
            label_fields=['gt_bboxes_labels', 'gt_ignore_flags']),
        keymap={
            'img': 'image',
            'gt_bboxes': 'bboxes'
        }),
    dict(type='YOLOv5HSVRandomAug'),
    dict(type='mmdet.RandomFlip', prob=0.5),
    dict(
        type='mmdet.PackDetInputs',
        meta_keys=(
            'img_id', 'img_path', 'ori_shape', 'img_shape', 'flip',
            'flip_direction'))
]

train_dataloader = dict(
    batch_size=train_batch_size_per_gpu,
    num_workers=train_num_workers,
    persistent_workers=persistent_workers,
    pin_memory=True,
    sampler=dict(type='DefaultSampler', shuffle=True),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        ann_file='annotations/instances_train2017.json',
        data_prefix=dict(img='train2017/'),
        filter_cfg=dict(filter_empty_gt=False, min_size=32),
        pipeline=train_pipeline))

test_pipeline = [
    dict(type='LoadImageFromFile', file_client_args=_base_.file_client_args),
    dict(type='YOLOv5KeepRatioResize', scale=img_scale),
    dict(
        type='LetterResize',
        scale=img_scale,
        allow_scale_up=False,
        pad_val=dict(img=114)),
    dict(type='LoadAnnotations', with_bbox=True, _scope_='mmdet'),
    dict(
        type='mmdet.PackDetInputs',
        meta_keys=(
            'img_id', 'img_path', 'ori_shape', 'img_shape', 'scale_factor',
            'pad_param'))
]

val_dataloader = dict(
    batch_size=val_batch_size_per_gpu,
    num_workers=val_num_workers,
    persistent_workers=persistent_workers,
    pin_memory=True,
    drop_last=False,
    sampler=dict(type='DefaultSampler', shuffle=False),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        test_mode=True,
        data_prefix=dict(img='val2017/'),
        ann_file='annotations/instances_val2017.json',
        pipeline=test_pipeline,
        batch_shapes_cfg=batch_shapes_cfg))

test_dataloader = val_dataloader

param_scheduler = None
optim_wrapper = dict(
    type='OptimWrapper',
    optimizer=dict(
        type='SGD',
        lr=base_lr,
        momentum=0.937,
        weight_decay=0.0005,
        nesterov=True,
        batch_size_per_gpu=train_batch_size_per_gpu),
    constructor='YOLOv5OptimizerConstructor')

default_hooks = dict(
    param_scheduler=dict(
        type='YOLOv5ParamSchedulerHook',
        scheduler_type='linear',
        lr_factor=0.01,
        max_epochs=max_epochs),
    checkpoint=dict(
        type='CheckpointHook',
        interval=save_epoch_intervals,
        save_best='auto',
        max_keep_ckpts=3))

custom_hooks = [
    dict(
        type='EMAHook',
        ema_type='ExpMomentumEMA',
        momentum=0.0001,
        update_buffers=True,
        strict_load=False,
        priority=49)
]

val_evaluator = dict(
    type='mmdet.CocoMetric',
    proposal_nums=(100, 1, 10),
    ann_file=data_root + 'annotations/instances_val2017.json',
    metric='bbox')
test_evaluator = val_evaluator

train_cfg = dict(
    type='EpochBasedTrainLoop',
    max_epochs=max_epochs,
    val_interval=save_epoch_intervals)
val_cfg = dict(type='ValLoop')
test_cfg = dict(type='TestLoop')
