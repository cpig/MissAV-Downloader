# !Warning!
2026 Jul:
MissAV site has lauched more strict anti-crawler technique, and this method does not work anymore.
I am sorry. 





## 下载

- 添加新电影到待下载库中

```python main.py add -i sone-764,sone-123```

- 批量下载库中电影

```python main.py download```

- 直接下载一个电影，如sone-764

```python main.py download -i sone-764```

## 查询

- 展示库中单条电影详细信息

```python main.py list -i sone-764```

- 展示库中所有状态waiting的电影

```python main.py list -s waiting```

- 展示库中所有标题包含愛才りあ的电影

```python main.py list -k 愛才りあ```

- 展示库中所有状态waiting且标题包含愛才りあ的电影

```python main.py list -s waiting -k 愛才りあ```

## 修改

- 删除一条库中电影

```python main.py delete -i sone-764```

- 修改电影状态为已完成

```python main.py change -i sone-764 -s finished```
