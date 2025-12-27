# MissAV-Downloader V0.1

The project is still under development.


- 添加新电影到待下载库中：

```python main.py add -i sone-764,sone-123```

- 批量下载库中电影：

```python main.py download```

- 直接下载一个电影，如sone-764：

```python main.py download -i sone-764```

- 展示库中单条电影详细信息：

```python main.py list -i sone-764```

- 删除一条库中电影

```python main.py delete -i sone-764```

- 修改电影状态为已完成

```python main.py change -i sone-764 -c finished```