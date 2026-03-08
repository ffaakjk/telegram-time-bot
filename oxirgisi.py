from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from datetime import datetime, time
import openpyxl
import math
import asyncio

TOKEN="8599625661:AAFHXMs5t4Vf-EApD-hfUS0_r2S3DplRWwY"

WORK_LAT=40.1116843
WORK_LON=65.3760140

WORK_START=time(9,0)
WORK_END=time(22,0)

admins=[2013863098]

workers={}
start_times={}
worker_locations={}
salary_today=[]
salary_week={}
late_workers=[]
pending_check={}
verified_workers={}

keyboard=[["START","STOP"]]
markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True)

admin_keyboard=ReplyKeyboardMarkup([
["📊 REPORT","👥 WHO WORKING"],
["📍 MAP","⏰ LATE"],
["💰 WEEK SALARY","➕ ADD WORKER"]
],resize_keyboard=True)


def distance(lat1,lon1,lat2,lon2):
    return math.sqrt((lat1-lat2)**2+(lon1-lon2)**2)


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user=update.message.from_user.id

    if user in admins:
        await update.message.reply_text("👑 ADMIN PANEL",reply_markup=admin_keyboard)
    else:
        await update.message.reply_text("👷 Worker panel",reply_markup=markup)


async def add(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id not in admins:
        return

    try:
        uid=int(context.args[0])
        name=context.args[1]
        rate=int(context.args[2])
    except:
        await update.message.reply_text("Usage:\n/add telegram_id name rate")
        return

    workers[uid]=[name,rate]

    await update.message.reply_text(f"✅ Worker {name} added")


async def photo(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.message.from_user.id

    if user not in workers:
        return

    pending_check[user]=datetime.now()

    await update.message.reply_text("📍 Send GPS location")


async def location(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.message.from_user.id

    if user not in workers:
        return

    if user not in pending_check:
        await update.message.reply_text("📷 Send selfie first")
        return

    lat=update.message.location.latitude
    lon=update.message.location.longitude

    dist=distance(lat,lon,WORK_LAT,WORK_LON)

    if dist>0.003:

        for admin in admins:
            await context.bot.send_message(admin,f"⚠ {workers[user][0]} left work location")

        await update.message.reply_text("❌ You are not at work location")
        return

    verified_workers[user]=datetime.now()
    worker_locations[user]=(lat,lon)

    del pending_check[user]

    await update.message.reply_text("✅ Selfie + GPS accepted")


async def message(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.message.from_user.id
    text=update.message.text

    if user in admins:
        if text=="➕ ADD WORKER":

            await update.message.reply_text(
                "Send like this:\n\n"
                "/add telegram_id name rate\n\n"
                "Example:\n"
                "/add 123456789 Ali 10000"
            )

            return

        if text=="📍 MAP":

            for uid in worker_locations:

                lat,lon=worker_locations[uid]
                name=workers[uid][0]

                await context.bot.send_location(update.message.chat_id,lat,lon)
                await update.message.reply_text(name)

            return


        if text=="👥 WHO WORKING":

            txt="👥 Working now\n\n"

            for uid in start_times:
                txt+=workers[uid][0]+"\n"

            await update.message.reply_text(txt)

            return


        if text=="⏰ LATE":

            txt="⏰ Late workers\n\n"

            for w in late_workers:
                txt+=w+"\n"

            await update.message.reply_text(txt)

            return


        if text=="📊 REPORT":

            wb=openpyxl.Workbook()
            ws=wb.active

            ws.append(["Worker","Start","End","Hours","Salary"])

            for r in salary_today:
                ws.append(r)

            wb.save("report.xlsx")

            await update.message.reply_document(open("report.xlsx","rb"))

            return


        if text=="💰 WEEK SALARY":

            txt="💰 Weekly salary\n\n"

            for w in salary_week:
                txt+=f"{w} : {salary_week[w]}\n"

            await update.message.reply_text(txt)

            return


    if user not in workers:
        return


    name,rate=workers[user]


    if text=="START":

        if user not in verified_workers:

            await update.message.reply_text("📷 Send selfie + GPS first")
            return

        start_times[user]=datetime.now()

        if datetime.now().time()>WORK_START:
            late_workers.append(name)

        await update.message.reply_text(f"{name} started work")



    if text=="STOP":

        if user not in start_times:
            return

        start=start_times[user]
        end=datetime.now()

        hours=(end-start).seconds/3600

        pay=round(hours*rate)

        salary_today.append([name,start.strftime("%H:%M"),end.strftime("%H:%M"),round(hours,2),pay])

        if name not in salary_week:
            salary_week[name]=0

        salary_week[name]+=pay

        await update.message.reply_text(f"{name}\nHours {round(hours,2)}\nSalary {pay}")

        del start_times[user]


async def auto_report(app):

    while True:

        now=datetime.now()

        if now.hour==22 and now.minute==0:

            wb=openpyxl.Workbook()
            ws=wb.active

            ws.append(["Worker","Start","End","Hours","Salary"])

            for r in salary_today:
                ws.append(r)

            wb.save("daily.xlsx")

            for admin in admins:
                await app.bot.send_document(admin,open("daily.xlsx","rb"))

        await asyncio.sleep(60)



async def stop_reminder(app):

    while True:

        if datetime.now().hour>=22:

            for uid in start_times:

                for admin in admins:

                    await app.bot.send_message(admin,f"⚠ {workers[uid][0]} forgot STOP")

        await asyncio.sleep(1800)



app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("add",add))

app.add_handler(MessageHandler(filters.TEXT,message))
app.add_handler(MessageHandler(filters.PHOTO,photo))
app.add_handler(MessageHandler(filters.LOCATION,location))

print("BOT STARTED")

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_polling())
