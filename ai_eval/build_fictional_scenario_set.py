"""Build a clearly fictional, development-only scenario set for DigitalWitness."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "fictional_scenario_set.jsonl"

# Each scenario has 32 fictional positive examples and 8 hard negatives.
# The examples describe messages or reports; they are not real evidence.
SCENARIOS = {
    "harassment_stalking": {
        "category": "cyberstalking_bullying",
        "positive": [
            "You can block this account too. I know which bus stop you use after class, and I will wait there Friday.",
            "I made another profile because you ignored the last one. I will keep messaging until you answer.",
            "You posted that cafe five minutes ago. I found your check-in and came here to watch you leave.",
            "I watched your location move from the library to home again. Turning it off will not help.",
            "The group chat has tagged me in every post since Monday and keeps telling others to pile on.",
            "I will be outside your office at closing time. You cannot keep avoiding this conversation.",
            "Every night this account calls me, hangs up, and sends another message after I block it.",
            "Nice try changing your username. I saved the old one and found this profile in two minutes.",
            "Reply by tonight or I will keep showing up wherever you check in.",
            "The messages stopped for a week, then a new account sent a photo of the street near my class.",
            "They keep posting my name in the gaming server and telling members to message me insults.",
            "I know your train time from your public stories. I will make sure you notice me tomorrow.",
            "The same person has sent 46 messages from five accounts since I said I wanted no contact.",
            "If you leave this chat, I will join every group you are in and make sure they hear about you.",
            "A user keeps tagging my workplace page with comments about my appearance after I asked them to stop.",
            "I am not going to stop contacting you. I will use a new number every time you block me.",
            "The account replied to an old photo with, 'I know where you go for your evening walk.'",
            "They send a blank call at midnight, then a message saying they were checking whether I was home.",
            "Three classmates keep sharing my profile in a group and telling people to mock my posts.",
            "I will wait near the coaching center tomorrow. You can keep changing your route if you want.",
            "After I blocked him, he contacted my coworkers asking which days I am in the office.",
            "This new account knows the nickname only my old group used and says it has been watching me.",
            "I told the server moderator to stop the dogpile; the user came back with another account and restarted it.",
            "The comments appear under every public post within minutes, calling me names and asking where I live.",
            "I saved screenshots of the repeated messages. The sender says they will keep following my accounts.",
            "They keep sending requests from new profiles and write, 'You cannot disappear from me.'",
            "Someone posted my usual study schedule in the class group and told others to wait for me there.",
            "The user has been watching my public live streams and says it can see when I leave the building.",
            "They are sending unwanted messages to my friends so those friends will pressure me to reply.",
            "A person from the old chat keeps making new accounts to contact me after I asked for no contact.",
            "The account says it will come to my workplace if I do not answer its messages tonight.",
            "They keep humiliating me in the group and now say they will find me after the event.",
        ],
        "negative": [
            "My sister and I share live location during the trip because we both agreed to it.",
            "The safety guide explains how to turn off location sharing and restrict message requests.",
            "The film script has a fictional character who follows someone; no real person is being contacted.",
            "A moderator muted the whole chat for the evening so members could cool down after an argument.",
            "I changed my privacy settings after reading an article about unwanted online contact.",
            "The group is reminding everyone to meet at the public entrance at six; nobody is being singled out.",
            "My friend sent one check-in message after our agreed meeting time and stopped when I replied.",
            "This training slide describes blocking and reporting tools without showing an actual incident.",
        ],
    },
    "extortion_blackmail": {
        "category": "blackmail_threatening",
        "positive": [
            "Send the money tonight or I will forward our private chat to your family group.",
            "Transfer the amount I asked for, or I will send these screenshots to your manager tomorrow.",
            "You have until 8 p.m. to pay me. After that I am posting the messages you wanted kept private.",
            "I will delete the copied files only after you send the payment. Do not tell anyone.",
            "Send a gift card code and I will keep your account name out of the public post.",
            "If you do not give me the money, I will email your school with the edited conversation.",
            "The sender says they will publish my private messages unless I pay before the weekend.",
            "You can either send the money or I will share the screenshots with everyone in your contacts.",
            "I was asked to pay for silence about a private disagreement; the sender set a deadline.",
            "Pay me back twice what you borrowed or I will post your personal chat history.",
            "They say they will report me to my employer unless I send money to the account they named.",
            "The message demands a transfer and threatens to send my private details to a group if I refuse.",
            "I have saved your messages. Send the amount by midnight or I will make them public.",
            "The account says it will contact my relatives with a private screenshot unless I do what it asks.",
            "They are demanding a payment to remove a post they say they will publish about me.",
            "I got a voice note saying, 'Pay by Friday or I will send the recording to your team.'",
            "Give me the money and I will not tell your landlord about the conversation, the sender wrote.",
            "The person keeps raising the amount and says the screenshots will go to my parents if I stop replying.",
            "I am being pressured to send a transfer to keep a personal conversation from being exposed.",
            "The sender threatens to share my account details with my classmates unless I send the requested amount.",
            "They wrote that refusing to pay would mean my private messages are posted on their public page.",
            "The demand is for money by tonight, with a threat to forward the chat to my clients.",
            "They say they will make a complaint using my private messages unless I send them a payment.",
            "A stranger says it has copied my chat and wants money to keep it from being shared.",
            "Send the requested amount, the message says, or the sender will send my private email thread to the group.",
            "I was told to pay for the account to stop contacting my relatives with the screenshots.",
            "The person demands money to delete a copied file and says it will publish the file if I do not pay.",
            "The voice note links a payment deadline to a threat to expose my private conversation.",
            "They say I must do what they ask or they will send the screenshots to my course coordinator.",
            "A new account demands money and says it will keep posting about me until I pay.",
            "The message says, 'Send the transfer now, or I will share the private notes you sent me.'",
            "The sender says it will reveal a personal secret to my family unless I follow its demand.",
        ],
        "negative": [
            "Your invoice is due on the 30th; contact billing if you think the amount is wrong.",
            "My roommate asked me to return the money I borrowed, and we agreed on a date.",
            "The bank notice says a late fee may apply under the account terms; it does not ask for secrecy.",
            "A classroom example explains what blackmail means using a made-up story.",
            "The support team says it will review my report and send an update when it has a result.",
            "My friend warned me that a stranger may be trying to pressure people for money online.",
            "The seller offered a refund or replacement for the damaged item, and I chose the refund.",
            "The movie character asks for payment in a fictional scene; this is a review of the film.",
        ],
    },
    "intimate_image_abuse": {
        "category": "intimate_image_abuse",
        "positive": [
            "I will share your private photos with your family if you do not reply tonight.",
            "The screenshot shows a message threatening to post an intimate image; no image was attached.",
            "Send me what I asked for or I will upload the private picture you shared with me.",
            "They say they will forward a private image to my classmates unless I meet them.",
            "A stranger threatens to send a fabricated intimate picture to my contacts. I do not have that image.",
            "The account wrote, 'I will make a fake private picture of you and send it to your office.'",
            "I have only the threat message. It says the sender will publish a private photo if I refuse.",
            "They keep asking me for an intimate picture and say they will post a fake one if I say no.",
            "The sender threatens to put a private image on a public page and tag my relatives.",
            "A direct message says it has a private photo and will send it to my course group unless I comply.",
            "They threatened to create an altered intimate image and use it to embarrass me online.",
            "The account says it will share a private photo with my employer unless I send money.",
            "I was told that a private image would be posted tonight; there was no file in the chat.",
            "The message threatens to send an intimate picture to my family group after I ended the conversation.",
            "A user says it will upload a fake intimate image using my profile picture if I block it.",
            "The sender demands that I keep talking or it will circulate the private image it claims to have.",
            "I received a threat to share intimate pictures with my friends. I have screenshots of the threat only.",
            "They wrote that they would make a fake image and label it with my name unless I obeyed.",
            "A message says, 'I will send your private photo to the class chat tomorrow.'",
            "The account is pressuring me to meet and threatens to publish a private image if I refuse.",
            "The sender says a manipulated intimate picture will go to my family unless I pay.",
            "I was threatened with the circulation of a private image after asking the person to delete it.",
            "The chat contains a demand and a threat to share an intimate photo; the photo itself is not included.",
            "They threatened to tag my workplace in a post containing a private image of me.",
            "The profile says it will send a fake intimate picture to my partner to cause trouble.",
            "A person threatens to publish a private image unless I withdraw a complaint I made online.",
            "The message threatens to send an intimate photo to my contacts list; I never uploaded one here.",
            "They say they will create a fake intimate image with my face and post it unless I meet their demand.",
            "The sender threatens to circulate private pictures from an old chat after I asked for no contact.",
            "A group member says it will share an intimate image of me in the community channel tonight.",
            "The account threatens to post a fabricated private picture and claims it can make it look real.",
            "I have a screenshot where the sender threatens to share my intimate image with my relatives.",
        ],
        "negative": [
            "The help article says people can begin a report with screenshots of threats; an intimate image is not required.",
            "Our media-literacy class discussed consent and image privacy using a fictional scenario.",
            "My partner asked before sharing our ordinary vacation photo, and I said yes.",
            "The platform page explains how to report non-consensual image sharing without displaying any image.",
            "The film review mentions a fictional blackmail plot but describes no real message or person.",
            "I am checking whether my account has a setting that prevents others from saving profile pictures.",
            "The counselor told us to keep threatening messages and not to seek out or download intimate material.",
            "A public awareness post explains that a missing provenance record does not prove an image is fake.",
        ],
    },
    "defamation_morphing": {
        "category": "defamation_morphing",
        "positive": [
            "Someone edited my photo and added a caption falsely claiming I stole money from the club.",
            "The account posted a fabricated screenshot with my name and words I never wrote.",
            "They altered a short clip so it sounds like I insulted a coworker, then tagged my team.",
            "A false accusation about me is being shared with a doctored image as if it were proof.",
            "The group admin says the image was edited to make me appear at an event I never attended.",
            "A user sent my employer an edited picture with a false claim about my conduct.",
            "The post attributes a made-up confession to me and uses a cropped chat screenshot.",
            "They changed the text on my public post and shared the altered version under my name, making it look like I wrote it.",
            "I received a threat to circulate a fake screenshot that accuses me of cheating customers.",
            "The account is spreading a false allegation about me with an image that appears digitally changed.",
            "Someone added my face to a misleading collage and sent it to the neighborhood group.",
            "The clip is edited to remove the part where I disagreed; the caption falsely says I approved the decision.",
            "A fake quote card uses my photograph and attributes a hateful statement to me.",
            "They say they will keep sharing a doctored picture that falsely accuses me of misconduct.",
            "My name is attached to an audio clip I did not record, and the post presents it as my voice.",
            "A class group is circulating an edited screenshot that makes it look like I threatened someone.",
            "The account paired my image with a false claim and tagged people from my workplace.",
            "Someone altered the date and wording on a chat image to make me look responsible for a loss.",
            "They posted a manipulated video and wrote that it proves I said something I never said.",
            "A false rumor about my work is being spread alongside an image with my face pasted into it.",
            "The sender threatens to publish an edited chat that makes my private reply look like an admission.",
            "A fake notice uses my photo and falsely says I was removed from the student group for misconduct.",
            "They have changed the caption on an old photo to accuse me of taking a payment.",
            "A profile shared an altered image of me with a false statement about my family.",
            "The message says the edited clip will be sent to my clients to damage my reputation.",
            "Someone made a fake screenshot of my account and claims I posted a threatening message.",
            "A cropped recording leaves out my answer and is being shared with a misleading accusation.",
            "The post uses a digitally altered picture to support a false claim about my conduct.",
            "They are sending a fabricated conversation to my classmates and saying I wrote the insulting line, which I never wrote.",
            "A social account reposted a changed image with my name and a false allegation about the fundraiser.",
            "The sender says it will spread a misleading edited video unless I withdraw my correction.",
            "I reported a fake quote image that uses my profile photo and words I did not say.",
        ],
        "negative": [
            "I cropped my own landscape photo and adjusted the brightness before posting it.",
            "The clearly labeled parody account uses an obviously fictional cartoon edit for a joke.",
            "Our class is learning how to check a picture's source before repeating a claim.",
            "I asked the poster where the quote came from because I could not verify it.",
            "The event photographer corrected the color balance with the subject's approval.",
            "A news article discusses how edited images can mislead people; it names no target.",
            "The drama club shared a labeled promotional poster for a fictional courtroom play.",
            "I corrected a typo in my own caption and reposted the same photograph.",
        ],
    },
    "fake_profile_impersonation": {
        "category": "fake_profile_impersonation",
        "positive": [
            "A new account copied my profile photo and is asking my friends to send it money.",
            "Someone made a fake account in my name and messaged my manager as if it were me.",
            "The profile uses my pictures and tells people it is my backup account, but I did not create it.",
            "My cousin received a message from an account pretending to be me and asking for an urgent transfer.",
            "They are using my identity to message members of the group after I blocked the original profile.",
            "A lookalike page copied my bio and is replying to customers as though it runs my shop.",
            "The account uses my photo and name, then asks people for private details in my name.",
            "I found a fake profile using my identity to message my classmates about a made-up event.",
            "Friends say a lookalike account with one extra character is messaging them and asking for money as if it were me.",
            "The user is impersonating me online and sent a false announcement to the community page.",
            "A copy of my profile is contacting relatives and claiming I changed my phone number.",
            "Someone created a fake account in my name and posted a link as if I endorsed it.",
            "The account copied my pictures and is asking my clients to pay a different account.",
            "They made a profile with my name and are replying to messages I never received.",
            "A fake page using my identity is inviting people to a private group I do not run.",
            "My friends received a message from a lookalike account pretending to be me and asking them to keep it secret.",
            "A profile with my photo claims to be my official account, but I have only one account.",
            "The new account is impersonating me in the team chat and changing details about the meeting.",
            "Someone copied the shop logo and my profile image, then told customers to send payments there.",
            "The fake account used my name to contact a relative and ask for a personal document.",
            "A stranger's account is pretending to be me in comments and telling people I approved their fundraiser.",
            "They opened another account with my pictures and are pretending to be me after the platform removed the first copy.",
            "The cloned profile messages my followers and asks them to share a one-time code.",
            "My colleague sent a screenshot of an account using my identity to request a confidential file.",
            "A fake profile uses my photo and says it is my new account, but the contact link is unfamiliar.",
            "The person copied my name and profile image to send messages to members of my class group.",
            "An account I never authorized copied my shop name and replies as though it were my business account.",
            "Someone is using my identity to ask my friends for a loan I never requested.",
            "A cloned account has my old profile picture and tells people I am collecting donations for a cause.",
            "A fake account in my name is sharing posts and tagging people who know me offline.",
            "They copied my profile and are asking my contacts to move the conversation to another app.",
            "My family says a profile pretending to be me sent them a link and asked them to log in.",
        ],
        "negative": [
            "The parody profile says in its bio that it is fictional and is not affiliated with me.",
            "Our club account is shared by three admins, and each one has permission to post updates.",
            "The verified profile is my official account; the platform badge and link match my website.",
            "A fan page uses my public work and clearly says it is run by a fan, not by me.",
            "I made a second account for photography and linked it from my main profile.",
            "The fictional character account is part of a role-play group and does not claim to be a real person.",
            "The organization asked me to create its page and authorized me to reply to customer questions.",
            "The platform help page explains how to report a profile that is pretending to be someone else.",
        ],
    },
}


def build_cases() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_text: set[str] = set()
    for scenario, config in SCENARIOS.items():
        positive = config["positive"]
        negative = config["negative"]
        if len(positive) != 32 or len(negative) != 8:
            raise ValueError(f"{scenario} must have exactly 32 positive and 8 negative cases")
        for expected_threat, examples in ((True, positive), (False, negative)):
            for text in examples:
                normalized = re.sub(r"\W+", " ", text.casefold()).strip()
                if normalized in seen_text:
                    raise ValueError(f"Duplicate fictional text: {text}")
                seen_text.add(normalized)
                rows.append({
                    "id": f"fictional-{len(rows) + 1:03d}",
                    "split": "fictional_development",
                    "source": "author_written_synthetic",
                    "label_status": "not_independently_reviewed",
                    "language": "en",
                    "scenario": scenario,
                    "expected_threat": expected_threat,
                    "expected_category": config["category"] if expected_threat else None,
                    "text": text,
                })
    if len(rows) != 200:
        raise ValueError(f"Expected 200 examples, got {len(rows)}")
    return rows


def main() -> None:
    rows = build_cases()
    OUTPUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} unique fictional examples to {OUTPUT.name}.")


if __name__ == "__main__":
    main()
