# 开发规范

## 代码风格

- 使用 Python 3.10+ 语法
- 遵循 PEP 8 规范
- 使用 `black` 格式化代码
- 使用 `flake8` 检查代码质量
- 使用 `mypy` 进行类型检查

## 命名规范

- 文件名：snake_case（如 `data_loader.py`）
- 类名：PascalCase（如 `SemanticSegmentation`）
- 函数名：snake_case（如 `load_image`）
- 常量：UPPER_SNAKE_CASE（如 `MAX_IMAGE_SIZE`）
- 变量：snake_case（如 `image_path`）

## 目录结构

```
src/
├── data/              # 数据加载和处理
├── preprocessing/     # 影像预处理
├── models/           # 模型定义
├── training/         # 训练脚本
├── inference/        # 推理脚本
├── postprocessing/   # 后处理
├── evaluation/       # 评估脚本
├── vectorization/    # 图斑矢量化
└── utils/            # 工具函数
```

## Git 提交规范

提交信息格式：
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码风格调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：
```
feat(preprocessing): 添加影像配准算法

- 实现基于特征点的自动配准
- 支持 SIFT 和 ORB 两种算法
- 添加单元测试

Closes #123
```

## 分支管理

- `main`: 主分支，保持稳定
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: 修复分支
- `release/*`: 发布分支

## 测试规范

- 每个模块必须有对应的单元测试
- 测试覆盖率 ≥ 80%
- 使用 pytest 框架
- 测试文件命名：`test_*.py`

## 文档规范

- 所有公开函数必须有 docstring
- 使用 Google 风格 docstring
- 复杂算法需要写设计文档
- API 变更需要更新文档

## 代码审查

- 所有代码必须经过 review 才能合并
- 至少 1 人 approve
- CI 必须通过（lint + test）
