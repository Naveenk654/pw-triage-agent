import os
import smtplib
import time
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

if not GMAIL_USER or not GMAIL_APP_PASSWORD:
    print("Error: GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
    exit(1)

# 30 Realistic Student Emails (Categories are NOT mentioned in the text)
EMAILS = [
    # --- TECHNICAL (5) ---
    ("App is totally freezing during live class", "Bhai mera app live class ke beech mein freeze ho jata hai, aur screen black ho jati hai. Pura app restart karna padta hai. Device Realme 8 hai. Please fix this fast, backlog ban raha hai."),
    ("Video player error 404", "Whenever I try to play recorded lectures of Physics, it shows error 404 and doesn't load. My internet is 100mbps so that is not the issue. Help me out."),
    ("Login problem on web version", "I am trying to login on my laptop browser (Chrome) but after entering OTP it just redirects me back to the login page. Works fine on my mobile. Why?"),
    ("Audio out of sync in recordings", "Sir in yesterday's chemistry lecture, the audio is completely out of sync with the video after the 30 minute mark. It is very confusing to study like this."),
    ("App crashes on startup", "I updated the app today morning from Playstore and now it just crashes immediately when I open it. I have already cleared cache and reinstalled but no use."),

    # --- REFUND (5) ---
    ("Want my money back", "I accidentally bought the Arjuna JEE batch yesterday but I am actually a NEET student. I haven't watched any videos yet. Please refund my money so I can buy the correct batch."),
    ("Double payment deducted", "I was trying to pay for Lakshya batch, the first transaction failed so I paid again. Now I see money is deducted TWICE from my bank account. Please refund the extra amount immediately!!"),
    ("Unhappy with the batch", "The pace of this batch is too fast for me and I cannot understand the math lectures. It has been only 2 days since I bought it. Can I get a refund?"),
    ("Parents bought wrong course", "My father mistakenly purchased the Class 11 batch instead of Dropper batch. We cannot afford to buy another one. Can you cancel this and refund it?"),
    ("Cancel my subscription", "I got admission into a local offline coaching so I no longer need this online batch. Please cancel my access and process a refund for the remaining months."),

    # --- ACADEMIC (6) ---
    ("Syllabus for upcoming mock test?", "Sir, what is the exact syllabus for the AITS mock test scheduled for this Sunday? Is rotational motion included in Physics or only up to center of mass?"),
    ("Doubt engine not answering", "I posted a doubt regarding organic chemistry nomenclature 2 days ago in the doubt section but still haven't received any reply from the faculties. My exam is near."),
    ("DPP solutions are wrong", "In yesterday's math DPP (Integration), the answer given for question 5 and 7 is incorrect. I checked with my teacher as well. Please update the solution PDF."),
    ("Which book to solve?", "I am in class 11. Along with PW modules, should I also solve HC Verma for physics or are the modules enough for JEE Advanced? Please guide."),
    ("Video solution for test?", "Will we get detailed video solutions for yesterday's minor test? The text solutions are a bit hard to understand for the tough chemistry questions."),
    ("Backlog strategy", "I joined the batch 1 month late and I have a huge backlog in Physics and Math. Should I watch old lectures or continue with live classes and do backlog on Sundays?"),

    # --- ACCOUNT (4) ---
    ("Change my registered mobile number", "I lost my old sim card and got a new phone number. How can I update my PW account with my new mobile number so I can receive OTPs?"),
    ("Forgot my password", "I am trying to login on my tablet but I forgot my password. When I click forgot password, the OTP is not coming to my email. Please help."),
    ("Profile name is spelled wrong", "During registration I made a typo in my name. It says 'Naveen Kamawat' instead of 'Naveen Kumawat'. How can I edit my profile name?"),
    ("Can I use on two devices?", "Is it possible to login to my PW account on both my Android phone and my Windows laptop at the same time? Or will my account get blocked?"),

    # --- BATCH ACCESS (5) ---
    ("Paid but batch not showing", "I paid for the Vidyapeeth online batch 2 hours ago and got the bank SMS, but when I open the app it still asks me to 'Buy Now'. Please activate my batch!"),
    ("Khazana access missing", "I bought the Lakshya batch along with the Khazana add-on, but I cannot see the Khazana section anywhere in my study tab. Where is it?"),
    ("Test series not unlocking", "I purchased the combo offer which includes the batch + test series. The batch lectures are working fine but the AITS tests are showing locked and asking for payment."),
    ("Cannot access old class 11 batch", "I am now in class 12 and bought the dropper batch. But I want to revise some class 11 topics. Why was my class 11 batch removed from my account?"),
    ("Module delivery status", "I ordered the physical study material (modules) 10 days ago but the tracking link is not working and I haven't received them yet. What is the status?"),

    # --- PAYMENT (3) ---
    ("EMI option not working", "I want to purchase the batch using Bajaj Finserv EMI card, but on the checkout page, it says my card is not supported. Why is this happening?"),
    ("Discount code invalid", "I am trying to apply the festive discount coupon code 'DIWALI20' but it says the coupon is invalid or expired. Today is the last date of the offer!"),
    ("Can I pay in installments?", "I cannot afford to pay the full 4000 rupees right now. Is there any monthly installment plan available for the online batches?"),

    # --- OTHER (2) ---
    ("Sir you are the best!", "I just wanted to say a huge thank you to Alakh sir and the entire team. Your lectures changed my life and I finally understand Physics! Love you guys!"),
    ("Need a discount please", "My family's financial condition is not very good. Can you please provide me a special discount or scholarship so I can study for NEET?"),
]

def send_test_emails():
    print(f"Connecting to Gmail SMTP server as {GMAIL_USER}...")
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    except Exception as e:
        print(f"Failed to login: {e}")
        return

    print("Successfully connected. Sending 30 realistic test emails to yourself...")
    
    for i, (subject, body) in enumerate(EMAILS, 1):
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER
        
        try:
            server.send_message(msg)
            print(f"[{i}/30] Sent: {subject}")
            # Sleep slightly to avoid being flagged as spam by Google
            time.sleep(1.5)
        except Exception as e:
            print(f"Failed to send email {i}: {e}")
            
    server.quit()
    print("\n✅ All 30 emails successfully sent!")
    print("They should now be arriving in your inbox as UNREAD.")
    print("Your listener script will automatically start fetching and triaging them!")

if __name__ == "__main__":
    send_test_emails()
