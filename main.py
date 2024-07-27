import json
import re
import datetime
import httpx
import certifi
from nextcord.ext import commands
import nextcord

config = json.load(open('./config.json', 'r', encoding='utf-8'))

bot = commands.Bot(
    command_prefix='nyx!',
    help_command=None,
    intents=nextcord.Intents.all(),
    strip_after_prefix=True,
    case_insensitive=True
)

class TopupModal(nextcord.ui.Modal):

    def __init__(self):
        super().__init__(title='เติมเงิน', timeout=None, custom_id='topup-modal')
        self.link = nextcord.ui.TextInput(
            label='ลิ้งค์ซองอังเปา',
            placeholder='https://gift.truemoney.com/campaign/?v=xxxxxxxxxxxxxxx',
            style=nextcord.TextInputStyle.short,
            required=True
        )
        self.add_item(self.link)

    async def callback(self, interaction: nextcord.Interaction):
        link = str(self.link.value).replace(' ', '')
        message = await interaction.response.send_message(content='checking.', ephemeral=True)
        if re.match(r'https:\/\/gift\.truemoney\.com\/campaign\/\?v=[a-zA-Z0-9]{18}', link):
            voucher_hash = link.split('?v=')[1]
            response = httpx.post(
                url=f'https://gift.truemoney.com/campaign/vouchers/{voucher_hash}/redeem',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/8a0.0.3987.149 Safari/537.36'
                },
                json={
                    'mobile': config['phoneNumber'],
                    'voucher_hash': voucher_hash
                },
                verify=certifi.where(),
            )
            if response.status_code == 200 and response.json()['status']['code'] == 'SUCCESS':
                data = response.json()
                amount = int(float(data['data']['my_ticket']['amount_baht']))
                userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
                if str(interaction.user.id) not in userJSON:
                    userJSON[str(interaction.user.id)] = {
                        "userId": interaction.user.id,
                        "point": amount,
                        "all-point": amount,
                        "transaction": [
                            {
                                "topup": {
                                    "url": link,
                                    "amount": amount,
                                    "time": str(datetime.datetime.now())
                                }
                            }
                        ]
                    }
                else:
                    userJSON[str(interaction.user.id)]['point'] += amount
                    userJSON[str(interaction.user.id)]['all-point'] += amount
                    userJSON[str(interaction.user.id)]['transaction'].append({
                        "topup": {
                            "url": link,
                            "amount": amount,
                            "time": str(datetime.datetime.now())
                        }
                    })
                json.dump(userJSON, open('./database/users.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
                embed = nextcord.Embed(description='✅﹒**เติมเงินสำเร็จ**', color=nextcord.Color.green())
            else:
                embed = nextcord.Embed(description='❌﹒**เติมเงินไม่สำเร็จ**', color=nextcord.Color.red())
        else:
            embed = nextcord.Embed(description='⚠﹒**รูปแบบลิ้งค์ไม่ถูกต้อง**', color=nextcord.Color.red())
        await message.edit(content=None, embed=embed)

class SellilvView(nextcord.ui.View):

    def __init__(self, message: nextcord.Message, value: str):
        super().__init__(timeout=None)
        self.message = message
        self.value = value

    @nextcord.ui.button(
        label='✅﹒ยืนยัน',
        custom_id='already',
        style=nextcord.ButtonStyle.primary,
        row=1
    )
    async def already(self, button: nextcord.Button, interaction: nextcord.Interaction):
        ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))
        userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
        if str(interaction.user.id) not in userJSON:
            embed = nextcord.Embed(description='🏦﹒เติมเงินเพื่อเปิดบัญชี', color=nextcord.Color.red())
        else:
            if userJSON[str(interaction.user.id)]['point'] >= ilvJSON[self.value]['price']:
                userJSON[str(interaction.user.id)]['point'] -= ilvJSON[self.value]['price']
                userJSON[str(interaction.user.id)]['transaction'].append({
                    "payment": {
                        "ilvId": self.value,
                        "time": str(datetime.datetime.now())
                    }
                })
                json.dump(userJSON, open('./database/users.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)

                embed = nextcord.Embed(description=f'🛒﹒ซื้อสินค้าสำเร็จ นี้คือลิ้งค์โหลด <{ilvJSON[self.value]["link"]}>', color=nextcord.Color.green())

                try:
                    dm_channel = await interaction.user.create_dm()
                    await dm_channel.send(embed=embed)
                except:
                    pass
            else:
                embed = nextcord.Embed(description=f'⚠﹒เงินของท่านไม่เพียงพอ ขาดอีก ({ilvJSON[self.value]["price"] - userJSON[str(interaction.user.id)]["point"]})', color=nextcord.Color.red())
        return await self.message.edit(embed=embed, view=None, content=None)

    @nextcord.ui.button(
        label='❌﹒ยกเลิก',
        custom_id='cancel',
        style=nextcord.ButtonStyle.red,
        row=1
    )
    async def cancel(self, button: nextcord.Button, interaction: nextcord.Interaction):
        return await self.message.edit(content='💚﹒ยกเลิกสำเร็จ', embed=None, view=None)

class SellilvSelect(nextcord.ui.Select):

    def __init__(self):
        options = []
        ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))
        for ilv in ilvJSON:
            options.append(nextcord.SelectOption(
                label=ilvJSON[ilv]['name'],
                description=ilvJSON[ilv]['description'],
                value=ilv,
                emoji=ilvJSON[ilv]['emoji']
            ))
        super().__init__(
            custom_id='select-ilv',
            placeholder='[ เลือกสินค้าที่คุณต้องการซื้อ ]',
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: nextcord.Interaction):
        message = await interaction.response.send_message(content='[SELECT] กำลังตรวจสอบ', ephemeral=True)
        selected = self.values[0]
        ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))
        embed = nextcord.Embed()
        embed.title = '»»———　ยืนยันการสั่งซื้อ　——-««'
        embed.description = f'''
        \n คุณแน่ใจหรอที่จะซื้อ : ** {ilvJSON[selected]['name']}** \n
        \n นี้คือตัวอย่างสินค้าที่จะซื้อ : {ilvJSON[selected]['example']} \n
        »»———　Hmhmhm　——-««
        '''
        embed.color = nextcord.Color.blue()
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/1224638859107762249/1224639590158303282/Black_and_White_Minimalist_Professional_Initial_Logo.png?ex=661e397e&is=660bc47e&hm=4796eb63b98a05949d8dd8c4a77790b7878184d6aea0f1766114c8864209fde5&')
        await message.edit(content=None, embed=embed, view=SellilvView(message=message, value=selected))

class SetupView(nextcord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SellilvSelect())

    @nextcord.ui.button(
        label='🧧﹒เติมเงิน',
        custom_id='topup',
        style=nextcord.ButtonStyle.primary,
        row=1
    )
    async def topup(self, button: nextcord.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(TopupModal())

    @nextcord.ui.button(
        label='💳﹒เช็คเงิน',
        custom_id='balance',
        style=nextcord.ButtonStyle.primary,
        row=1
    )
    async def balance(self, button: nextcord.Button, interaction: nextcord.Interaction):
        userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
        if str(interaction.user.id) not in userJSON:
            embed = nextcord.Embed(description='🏦﹒เติมเงินเพื่อเปิดบัญชี', color=nextcord.Color.red())
        else:
            embed = nextcord.Embed(description=f'```\n\n💳﹒ยอดเงินคงเหลือ {userJSON[str(interaction.user.id)]["point"]} บาท\n\n```', color=nextcord.Color.green())
        return await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(SetupView())
    print(f'LOGIN AS {bot.user}')

@bot.slash_command(
    name='setup',
    description='setup',
    guild_ids=[config['serverId']]
)
async def setup(interaction: nextcord.Interaction):
    if interaction.user.id not in config['ownerIds']:
        return await interaction.response.send_message(content='[ERROR] No Permission For Use This Command.', ephemeral=True)
    embed = nextcord.Embed()
    embed.title = '───                    Hmhmhm               ───'
    embed.description = f'''
    ```
    ─────────────────────────────────────

    ・ ✨﹒ระบบออโต้ 24 ชั่วโมง

    ─────────────────────────────────────```
    '''
    embed.color = nextcord.Color.blue()
    embed.set_image(url='https://images-ext-1.discordapp.net/external/JDnpFIEpRqs3lXwgtc6zk023mQP0KD5GDkXbRbWkAUM/https/www.checkraka.com/uploaded/img/content/130026/aungpao_truewallet_01.jpg')
    embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/1224638859107762249/1224639590158303282/Black_and_White_Minimalist_Professional_Initial_Logo.png?ex=661e397e&is=660bc47e&hm=4796eb63b98a05949d8dd8c4a77790b7878184d6aea0f1766114c8864209fde5&')
    await interaction.channel.send(embed=embed, view=SetupView())
    await interaction.response.send_message(content='[SUCCESS] Done.', ephemeral=True)

@bot.slash_command(
    name='addstock',
    description='Add a new stock item',
    guild_ids=[config['serverId']]
)
async def addstock(
    interaction: nextcord.Interaction,
    name: str,
    description: str,
    price: int,
    link: str,
    example: str,
    emoji: str
):
    try:
        with open('./database/ilvs.json', 'r', encoding='utf-8') as file:
            ilvJSON = json.load(file)
    except FileNotFoundError:
        ilvJSON = {}
    
    if name in [item['name'] for item in ilvJSON.values()]:
        return await interaction.response.send_message(content='[ERROR] Item with this name already exists.', ephemeral=True)
    
    ilvJSON[name] = {
        'name': name,
        'description': description,
        'price': price,
        'link': link,
        'example': example,
        'emoji': emoji
    }
    
    with open('./database/ilvs.json', 'w', encoding='utf-8') as file:
        json.dump(ilvJSON, file, indent=4, ensure_ascii=False)
    
    await interaction.response.send_message(content=f'[SUCCESS] Added new stock item: **{name}**', ephemeral=True)
    

@bot.slash_command(
    name='story',
    description='แสดงรายการสินค้าที่ซื้อไปแล้วและดาวน์โหลดอีกครั้ง',
    guild_ids=[config['serverId']]
)
async def story(interaction: nextcord.Interaction):
    userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
    ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))

    if str(interaction.user.id) not in userJSON or not userJSON[str(interaction.user.id)]['transaction']:
        embed = nextcord.Embed(description='❌﹒คุณยังไม่ได้ซื้อสินค้าใด ๆ', color=nextcord.Color.red())
    else:
        transactions = userJSON[str(interaction.user.id)]['transaction']
        embed = nextcord.Embed(title='รายการสินค้าที่ซื้อไปแล้ว', color=nextcord.Color.blue())
        for transaction in transactions:
            if 'payment' in transaction and 'ilvId' in transaction['payment']:
                ilvId = transaction['payment']['ilvId']
                if ilvId in ilvJSON:
                    product_name = ilvJSON[ilvId]['name']
                    download_link = ilvJSON[ilvId]['link']
                    purchase_time = transaction['payment']['time']
                    embed.add_field(name=product_name, value=f'ลิงก์ดาวน์โหลด: {download_link}\nเวลาที่ซื้อ: {purchase_time}', inline=False)
                else:
                    embed.add_field(name='Unknown Product', value='สินค้าไม่มีในระบบ', inline=False)
            else:
                embed.add_field(name='Unknown Transaction', value='ไม่มีข้อมูลการซื้อ', inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name='details', description='แสดงรายการสินค้าทั้งหมดที่มีพร้อมข้อมูลรายละเอียด')
async def details(interaction: nextcord.Interaction):
    ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))
    embed = nextcord.Embed(title='รายการสินค้าทั้งหมด', color=nextcord.Color.blue())
    for role in ilvJSON:
        embed.add_field(
            name=ilvJSON[role]['name'],
            value=f'รายละเอียด: {ilvJSON[role]["description"]}\nราคา: {ilvJSON[role]["price"]} บาท\nตัวอย่าง: {ilvJSON[role]["example"]}',
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.slash_command(
    name='profile',
    description='ดูโปรไฟล์ผู้ใช้',
    guild_ids=[config['serverId']]
)
async def profile(interaction: nextcord.Interaction):
    userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
    ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))

    if str(interaction.user.id) not in userJSON:
        embed = nextcord.Embed(description='❌﹒คุณยังไม่ได้ลงทะเบียนหรือเติมเงิน', color=nextcord.Color.red())
    else:
        user = userJSON[str(interaction.user.id)]
        points = user.get('point', 0)
        all_points = user.get('all-point', 0)
        
        transaction_history = "\n".join(
            [
                f"{t['payment']['time']}: {ilvJSON[t['payment']['itemId']]['name']}" 
                for t in user['transaction'] 
                if 'payment' in t and 'itemId' in t['payment'] and 'time' in t['payment']
            ]
        )

        embed = nextcord.Embed(title='โปรไฟล์ผู้ใช้', color=nextcord.Color.blue())
        embed.add_field(name='ยอดเงินคงเหลือ', value=f"{points} บาท", inline=False)
        embed.add_field(name='ยอดเงินทั้งหมดที่เติม', value=f"{all_points} บาท", inline=False)        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name='top', description='คนที่เติมเงินเยอะที่สุด')
async def top(interaction: nextcord.Interaction):
    userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
    top_users = sorted(userJSON.values(), key=lambda x: x['point'], reverse=True)[:10]
    embed = nextcord.Embed(title='กระดานคะแนน', color=nextcord.Color.blue())
    for i, user in enumerate(top_users, 1):
        embed.add_field(name=f'อันดับ {i}', value=f'ผู้ใช้: {user["userId"]} คะแนน: {user["all-point"]}', inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name='comment', description='อนุญาตให้ผู้ใช้ให้คะแนนและแสดงความคิดเห็นในสินค้าที่ซื้อ')
async def comment(interaction: nextcord.Interaction, product: str, rating: int, comment: str):
    ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))
    if product not in ilvJSON:
        await interaction.response.send_message('ไม่พบสินค้าที่คุณระบุ', ephemeral=True)
        return
    ilvJSON[product].setdefault('reviews', []).append({
        'user': interaction.user.id,
        'rating': rating,
        'comment': comment,
        'time': str(datetime.datetime.now())
    })
    json.dump(ilvJSON, open('./database/ilvs.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
    await interaction.response.send_message('ขอบคุณสำหรับการให้คะแนนและแสดงความคิดเห็น', ephemeral=True)

@bot.slash_command(name='average', description='แสดงคะแนนเฉลี่ยและรีวิวสำหรับแต่ละสินค้า')
async def average(interaction: nextcord.Interaction, product: str):
    ilvJSON = json.load(open('./database/ilvs.json', 'r', encoding='utf-8'))
    if product not in ilvJSON or 'reviews' not in ilvJSON[product]:
        await interaction.response.send_message('ไม่พบรีวิวสำหรับสินค้าที่คุณระบุ', ephemeral=True)
        return
    reviews = ilvJSON[product]['reviews']
    avg_rating = sum(review['rating'] for review in reviews) / len(reviews)
    embed = nextcord.Embed(title=f'คะแนนเฉลี่ยและรีวิวสำหรับ {ilvJSON[product]["name"]}', color=nextcord.Color.blue())
    embed.add_field(name='คะแนนเฉลี่ย', value=f'{avg_rating:.2f}', inline=False)
    for review in reviews:
        embed.add_field(name=f'ผู้ใช้ {review["user"]}', value=f'คะแนน: {review["rating"]}\nความคิดเห็น: {review["comment"]}', inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name='support', description='เพิ่มคำสั่งสนับสนุนเพื่อให้ผู้ใช้สามารถติดต่อขอความช่วยเหลือ')
async def support(interaction: nextcord.Interaction, message: str):
    guild = interaction.guild
    admin_role = guild.get_role(config['adminRoleId'])
    support_category = nextcord.utils.get(guild.categories, id=config['supportCategoryId'])  
    
    if not support_category:
        await interaction.response.send_message('ไม่พบหมวดหมู่สนับสนุน กรุณาลองใหม่ภายหลัง', ephemeral=True)
        return

    overwrites = {
        guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
        interaction.user: nextcord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    support_channel = await guild.create_text_channel(
        name=f'support-{interaction.user.name}',
        category=support_category,
        overwrites=overwrites
    )
    
    embed = nextcord.Embed(
        title="คำขอความช่วยเหลือ",
        description=message,
        color=nextcord.Color.blue(),
        timestamp=nextcord.utils.utcnow()
    )
    embed.add_field(name="ผู้ใช้", value=interaction.user.mention, inline=True)
    embed.add_field(name="ผู้ดูแลระบบ", value=admin_role.mention, inline=True)
    embed.set_footer(text="ระบบสนับสนุน")

    await support_channel.send(content=f'{admin_role.mention}', embed=embed)
    await interaction.response.send_message('คำขอความช่วยเหลือของคุณถูกส่งแล้วและได้สร้างห้องสนทนาส่วนตัว', ephemeral=True)


@bot.slash_command(
    name='qanda',
    description='แสดงคำถามที่พบบ่อย',
    guild_ids=[config['serverId']]
)
async def qanda(interaction: nextcord.Interaction):
    faqs = [
        {"question": "ซื้อสินค้าแล้วคืนเงินไหม?", "answer": "ไม่คืนเงิน"},
        {"question": "ซื้อสินค้าแล้วใช้ไม่ได้ทำไง?", "answer": "/support พร้อมข้อความมาได้เลย"}
    ]
    embed = nextcord.Embed(title='คำถามที่พบบ่อย', color=nextcord.Color.blue())
    for faq in faqs:
        embed.add_field(name=faq['question'], value=faq['answer'], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)



bot.run(config['token'])
