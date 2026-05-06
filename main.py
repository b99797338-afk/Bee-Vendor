import discord from discord.ext import commands from discord import app_commands import json

import os TOKEN = os.getenv("TOKEN")  # Railwayの環境変数から取得

intents = discord.Intents.default() bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "shop_data.json"

データ読み込み/保存

def load_data(): try: with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f) except: return {"products": {}, "channel": None, "log_channel": None}

def save_data(data): with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

商品追加コマンド（個別在庫対応）

@bot.tree.command(name="商品追加", description="商品を追加") async def add_product(interaction: discord.Interaction): class AddModal(discord.ui.Modal, title="商品追加"): name = discord.ui.TextInput(label="商品名") price = discord.ui.TextInput(label="値段") desc = discord.ui.TextInput(label="説明", style=discord.TextStyle.paragraph) contents = discord.ui.TextInput(label="商品内容（1行=1在庫 / 無限なら空）", style=discord.TextStyle.paragraph, required=False)

async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.contents.value.strip() == "":
            stock_list = []
            infinite = True
        else:
            stock_list = self.contents.value.split("\n")
            infinite = False

        data["products"][self.name.value] = {
            "price": self.price.value,
            "desc": self.desc.value,
            "items": stock_list,
            "infinite": infinite
        }

        save_data(data)
        await interaction.response.send_message(f"{self.name.value} を追加しました", ephemeral=True)

await interaction.response.send_modal(AddModal())

在庫確認

@bot.tree.command(name="在庫", description="在庫確認") async def stock(interaction: discord.Interaction): data = load_data() text = "" for name, info in data["products"].items(): if info.get("infinite"): s = "∞" else: s = len(info.get("items", [])) text += f"{name} : {s}\n"

await interaction.response.send_message(text or "商品なし", ephemeral=True)

チャンネル設定

@bot.tree.command(name="チャンネル設定", description="購入申請送信先") async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel): data = load_data() data["channel"] = channel.id save_data(data) await interaction.response.send_message("チャンネル設定完了", ephemeral=True)

ログチャンネル設定

@bot.tree.command(name="ログ設定", description="ログ送信先") async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel): data = load_data() data["log_channel"] = channel.id save_data(data) await interaction.response.send_message("ログチャンネル設定完了", ephemeral=True)

購入UI

class BuyView(discord.ui.View): def init(self): super().init(timeout=None)

data = load_data()
    options = []
    for name, info in data["products"].items():
        options.append(discord.SelectOption(label=name, description=info["desc"]))

    self.add_item(ProductSelect(options))

class ProductSelect(discord.ui.Select): def init(self, options): super().init(placeholder="商品を選択", options=options)

async def callback(self, interaction: discord.Interaction):
    product = self.values[0]

    class PayModal(discord.ui.Modal, title="送金リンク入力"):
        link = discord.ui.TextInput(label="送金リンク")

        async def on_submit(self, interaction: discord.Interaction):
            data = load_data()
            channel = bot.get_channel(data.get("channel"))

            embed = discord.Embed(title="購入申請")
            embed.add_field(name="商品", value=product)
            embed.add_field(name="購入者", value=interaction.user.mention)
            embed.add_field(name="リンク", value=self.link.value)

            view = ConfirmView(product, interaction.user.id, self.link.value)

            await channel.send(embed=embed, view=view)
            await interaction.response.send_message("送信しました", ephemeral=True)

    await interaction.response.send_modal(PayModal())

class ConfirmView(discord.ui.View): def init(self, product, user_id, pay_link): super().init(timeout=None) self.product = product self.user_id = user_id self.pay_link = pay_link

@discord.ui.button(label="承諾", style=discord.ButtonStyle.green)
async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
    data = load_data()
    product_data = data["products"][self.product]

    # 商品取得
    if product_data.get("infinite"):
        content = "（無限在庫商品）"
    else:
        if len(product_data["items"]) == 0:
            await interaction.response.send_message("在庫なし", ephemeral=True)
            return
        content = product_data["items"].pop(0)

    save_data(data)

    # DM送信
    user = await bot.fetch_user(self.user_id)
    await user.send(f"【購入完了】\n商品: {self.product}\n\n{content}")

    # ログ送信
    log_channel = bot.get_channel(data.get("log_channel"))
    if log_channel:
        embed = discord.Embed(title="購入ログ")
        embed.add_field(name="商品", value=self.product)
        embed.add_field(name="購入者", value=user.mention)
        embed.add_field(name="送金リンク", value=self.pay_link)
        embed.add_field(name="内容", value=content)
        await log_channel.send(embed=embed)

    await interaction.response.send_message("処理完了（商品送信＆ログ記録）", ephemeral=True)

自販機設置

@bot.tree.command(name="自販機設置", description="ショップ表示") async def setup_shop(interaction: discord.Interaction): data = load_data()

embed = discord.Embed(title="ショップ")

for name, info in data["products"].items():
    price = info["price"]
    desc = info["desc"]
    embed.add_field(name=f"{name} ({price})", value=desc, inline=False)

await interaction.channel.send(embed=embed, view=BuyView())
await interaction.response.send_message("設置完了", ephemeral=True)

@bot.event async def on_ready(): await bot.tree.sync() print(f"Logged in as {bot.user}")

bot.run(TOKEN)
