# MediaCrawler 二维码登录指南

## 方法1：自动运行（推荐）

在终端中运行：

```bash
cd ~/Desktop/MediaCrawler
python3 main.py --platform xhs --lt qrcode --type search --keywords "深圳找对象"
```

**流程：**
1. 浏览器窗口会自动弹出
2. 会看到小红书登录二维码
3. 打开手机小红书APP → 扫一扫
4. 确认登录
5. 登录成功后会自动爬取数据

**首次登录需要扫码，之后Cookie会自动保存。**

## 方法2：手动获取Cookie

如果自动登录有问题，可以手动获取Cookie：

### 步骤：

1. **打开浏览器开发者工具**
   - Chrome: F12 或 Cmd+Option+I (Mac)
   - 切换到 Network (网络) 标签

2. **访问小红书**
   ```
   https://www.xiaohongshu.com
   ```

3. **登录账户**
   - 扫码或手机号登录都可以

4. **复制Cookie**
   - 开发者工具 → Network
   - 刷新页面
   - 找到任意请求
   - Request Headers → Cookie
   - 复制整个Cookie字符串

5. **配置到MediaCrawler**
   - 编辑 `~/Desktop/MediaCrawler/config/xhs_config.py`
   - 找到 `COOKIES` 配置项
   - 粘贴Cookie字符串

### 配置示例：

```python
# xhs_config.py
XHS = {
    "COOKIES": "你的Cookie字符串",
    # ... 其他配置
}
```

## 验证登录成功

登录成功后，Cookie会保存在：
```
~/Desktop/MediaCrawler/cookies/xhs_cookies.json
```

下次运行时使用：
```bash
python3 main.py --platform xhs --lt cookie --type search --keywords "深圳找对象"
```

## 常见问题

### Q: 二维码显示后无法扫码？
A: 检查网络连接，确保能访问小红书。如果浏览器无法访问，检查代理设置。

### Q: 扫码后没有反应？
A: 等待1-2分钟，有时系统会有延迟。确保手机APP已登录。

### Q: Cookie有效期多久？
A: 通常7-30天。过期后重新扫码登录即可。

### Q: 服务器上如何使用？
A:
1. 本地登录获取Cookie
2. 复制 `cookies/xhs_cookies.json` 到服务器
3. 服务器上使用 `--lt cookie` 模式

## 快速测试

登录成功后，立即测试爬取：

```bash
# 爬取"深圳找对象"的前10条笔记
python3 main.py \
  --platform xhs \
  --lt cookie \
  --type search \
  --keywords "深圳找对象" \
  --max_notes 10
```

## 下一步

登录成功并验证可以爬取数据后：

1. **批量爬取多个关键词**
2. **导入到FindIt数据库**
3. **开始AI标签提取**

详细步骤见：`docs/AI_TAG_EXTRACTION.md`
