---
name: Sandbag
tagline: Log your lifts and find out which friend has been holding back.
status: shipping
stack: ["Expo", "React Native", "Fastify", "PostgreSQL"]
repo: https://github.com/KayraNafi/Sandbag
order: 0
showcase:
  - image: /images/apps/sandbag/active.webp
    width: 780
    height: 1688
    alt: A Push workout in progress. Bench press is ticked at 77.5 kg, and a banner says "77.5 kg again. Consistency, or fear?"
    title: Workout
    text: Starting a workout fills in the weight, sets and reps from your last session. You tick each lift when you finish it.
  - image: /images/apps/sandbag/call.webp
    width: 780
    height: 1688
    alt: A friend's Upper workout with bench press selected under "Which lift looks too easy?" and the accusation "RPE 9? You were texting."
    title: Calling sandbag
    text: On a friend's post, you pick a lift and write why you think it was too easy. A lift can only have one open call at a time.
  - image: /images/apps/sandbag/train.webp
    width: 780
    height: 1688
    alt: The home screen with the next workout, Push, above a card that says "Dex called sandbag. Squat, beat 105 kg."
    title: Home screen
    text: A call on you shows up here with the weight you have to beat. Your next session of that lift settles it.
  - image: /images/apps/sandbag/rankings.webp
    width: 780
    height: 1688
    alt: The weekly rankings. Each friend has a score, a progress percentage and a workout count. Bruno, in fifth place, has a sandbag badge.
    title: Rankings
    text: If you don't beat the weight, the sandbag badge stays next to your name for 7 days. Your score comes from your progress on your own lifts and how many workouts you did against your weekly target.
  - image: /images/apps/sandbag/exercise.webp
    width: 780
    height: 1688
    alt: Bench press progress, up 11 percent from 70 to 77.5 kg, with a line chart and a log of each session.
    title: Lift history
    text: Each lift has a chart of its weight per session and a log of every session.
---

My workouts lived in a WhatsApp chat, and finding last week's numbers meant
scrolling through it. Now I log them in an app my friends share, which works
offline and syncs when it gets a connection.

Friends can call you on a lift. Your next session of it settles the call, and
if you do not beat the number, you wear the badge in the rankings for a week.
Rankings use progress and consistency against your own numbers, so heavier
friends get no head start.

Invite-only and self-hosted: you run the server, and your crew's data stays on
it. Runs on Android. Apple users get the browser version, because I don't want
to pay the big corp $99 a year. If you are too lazy to add your workouts
yourself, create a personal API key and ask your AI agent to do it.
