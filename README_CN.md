# tg-shop-bot

**你的 Telegram 小店，能收 USDT——不用建网站、不用月费、半夜的订单也不会丢。**

English → [README.md](README.md)

## 演示

一条命令，零 API key、零网络，看完一整单：

```
$ python demo.py

  #1 手工香薰蜡烛 — 25.00 USDT
  #2 代购名额 — 99.00 USDT
  #3 内购情报频道 — 15.00 USDT（订阅制，30 天）

  小梅：/watch 1  → 已关注 #1，降价了我通知你。
  管理员：/price 1 19.99  → 1 位关注者收到通知
  >> 降价了：手工香薰蜡烛 现在 19.99 USDT（原价 25.00）。

  小梅：/buy 1
  机器人：订单 #1：手工香薰蜡烛 x1，共 19.99 USDT。
  小梅转了 19.99 USDT，然后：/pay 1 TXN7F2KQ9DEMO001
  机器人：TXID 已收到，卖家确认后订单即完成，一般几小时内。
  → 待审核：风险 0

  管理员：/approve 1 → 订单 #1 已付款，谢谢！

  阿 Leo 只转了 90 USDT 却下了 99 USDT 的单……
  → 待审核：风险 60（金额不符 + 首单大额）← 被标出来了
  管理员：/refund 2 → 订单 #2 已退款（金额不符）。

  管理员：/grant 1001 40 → 余额 40.00 USDT。
  小梅：/sub 3（从余额扣 15 USDT，不用 TXID）
  ……31 天后：从余额自动续费，剩余 10.00 USDT。
```

## 痛点

小梅在 Telegram 群里卖蜡烛，300 个老客。每单都是私聊、每笔付款都是截图、每句"你收到我的 USDT 了吗"都是 20 分钟拉扯。发售夜回不过消息就丢单——有一次地址看错，直接亏了 120 美元。

## 它能做什么

- **半夜的订单不会丢**——买家在 Telegram 里自己看、自己下单，你睡觉它也在卖货
- **收 USDT 不头疼**——买家转 USDT、粘贴 TXID，你点一下确认就行
- **骗子进不了门**——少转钱、TXID 重复用、首单大额，都会进审核队列并标风险分，而不是混进你的私聊
- **看过的人会回来买**——降价自动提醒关注的人，最便宜的"回头客营销"
- **老客一键付款**——余额支付，不用每次都走 TXID
- **订阅费自动到账**——从余额续费；余额不够就提醒买家充值，不会悄悄流失
- **中英双语**——一个机器人同时服务两拨客人

## 2 分钟上手

```bash
git clone https://github.com/webhookwizard/tg-shop-bot.git
cd tg-shop-bot
python demo.py          # 上面那一整单，离线跑，不用任何 key
```

真机上线：

```bash
pip install -r requirements.txt
cp .env.example .env    # 填 BOT_TOKEN（找 @BotFather 申请）+ ADMIN_IDS
python -m src.bot
```

## 工作原理

<details>
<summary>架构、两种收款方式、诚实说明</summary>

**技术：** Python 3.9+，Telegram 接 `python-telegram-bot`，其他全进 SQLite——一个文件就是全部账本（商品、订单、付款、审核、余额、关注、订阅）。备份就是复制一个文件。

**两种收款：**
1. **手动 TXID（默认，零 key）：**买家转 USDT 到你地址，用 `/pay` 提交交易号。每笔都进审核队列，你在链上看到钱了再点通过 / 退款 / 忽略。小卖家本来就是这么干的，机器人只是帮你理顺。
2. **CryptoBot（可选）：**填 `CRYPTOBOT_TOKEN` 就能开托管发票、自动到账确认。不填也完全能用。

**审核标记：**金额不符（+40）、首单≥$50（+20）、有过退款（+30），重复 TXID 直接拒绝。

**诚实说明：**
- 手动模式下机器人**看不到链**——你的眼睛就是验钞机，链上看到钱再点通过。
- 演示里都是模拟付款，没有真 USDT 流动。
- CryptoBot 是第三方服务，用之前去看它最新的费率和文档。

**真实成本：**软件 $0。买家付链上手续费（TRON 约 $1）。服务器：$5/月的 VPS 就够，或者你现在这台电脑。

**买家命令：**`/catalog` `/buy` `/pay` `/myorders` `/balance` `/watch` `/wishlist` `/sub` `/mysubs` · **管理员：**`/review` `/approve` `/refund` `/ignore` `/grant` `/addproduct` `/price`
</details>

## 省什么

不用 $29/月的 Shopify，不用 2.9% 的刷卡费，没有"不好意思私聊没回"——订单自己成交，你干别的去。

---

> 想按你的店定制一个？DM [@saulgoodmanc99](https://t.me/saulgoodmanc99) —— 定制 $99 起，只收 USDT。
