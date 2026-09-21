


# Interactive Prototyping: The Clock of Pi
**NAMES OF COLLABORATORS:** Afroza Aktar, Rawisara Chairat, Lamiah Khan, Xiaoxi Xu

**Please indicate anyone you collaborated with on this Lab here.**
Be generous in acknowledging their contributions! And also recognizing any other influences (e.g. from YouTube, Github, Twitter) that informed your design. 

***Update your [parts list inventory](partslist.md)***

## The Report
This readme.md page in your own repository should be edited to include the work you have done. You can delete everything but the headers and the sections between the \*\*\***stars**\*\*\*. Write the answers to the questions under the starred sentences. Include any material that explains what you did in this lab hub folder, and link it in the readme.

Labs are due on Sunday midnight. Make sure this page is linked to on your main class hub page.

## Part A. 
### Connect to your Pi

We connected to Raspberry Pi from laptop using PuTTY and SSH. We entered the Pi’s IP address and logged in with username and password. This allowed us to run commands on the Pi remotely.

**Image of terminal showing Raspberry Pi connected:**


<img width="811" height="506" alt="Part A" src="https://github.com/user-attachments/assets/6cac289e-a1d9-4442-8b9e-7b6ef6912b64" />
<br><br>

## Part B. 
### Try out the Command Line Clock

We cloned `Interactive-Lab-Hub` GitHub repository onto the Raspberry Pi. 
With the virtual environment active, I installed the required Python packages using `pip install -r requirements.txt`. I then ran the command-line clock with `python cli_clock.py`.

The program displayed the current date and time in the PuTTY terminal. The time updated every second on the same line. 


**Screenshot showing the command-line clock running in PuTTY:**


<img width="864" height="519" alt="image" src="https://github.com/user-attachments/assets/e902db1c-167c-438d-9c79-5832dc2ca74c" />


<br><br>

**Video showing the command-line clock running in PuTTY:**




https://github.com/user-attachments/assets/e442f8a7-4f2e-4afb-8b90-149c9dd062e1


<br><br>

## Part C. 
### Set up your RGB Display
For this part, we used the Adafruit MiniPiTFT display connected to my Raspberry Pi 5. The display communicates with the Pi using SPI. GPIO23 and GPIO24 connect to the two buttons, and GPIO22 controls the display’s backlight.

#### Displaying Info with Texts

We ran `piscreen.service` to display information about my Raspberry Pi, including its IP address, MAC address, memory usage, and CPU temperature. We also looked at `screen_boot_script.py` to understand how text is displayed. The program uses `draw.text()` to write information onto an image and `disp.image()` to show that image on the physical screen.

**Image showing Raspberry Pi displaying the system information, with unique MAC address:**



<img width="1600" height="1199" alt="IMG-20260913-WA0022" src="https://github.com/user-attachments/assets/f174eb07-fb2c-4b41-bd75-aa28e7915b48" />

<br><br>

Before running the other display programs, We stopped the startup service using `sudo systemctl stop piscreen.service`. This allowed the test program to use the display without another program trying to control the same pins.

### Testing your Screen

We then ran `python screen_test.py`, entered a color name red, and tested the buttons. With neither button pressed, the screen displayed green. Pressing button A displayed white, while pressing button B displayed red color. Pressing both buttons turned off the backlight. This showed that the display, buttons, and backlight responded to the program.

**Image showing Raspberry Pi successfully running the screen test:**

<img width="1600" height="1199" alt="IMG-20260913-WA0021" src="https://github.com/user-attachments/assets/05bb34b3-cd6d-4a78-ae72-5a1f5c12b1ef" />


<img width="1600" height="1199" alt="IMG-20260913-WA0019" src="https://github.com/user-attachments/assets/50189720-2e33-424d-9425-34bba6d663f9" />


<img width="1600" height="1200" alt="IMG-20260913-WA0020" src="https://github.com/user-attachments/assets/a99d85e2-1151-446c-9def-a3e8539b0828" />


<br><br>



**Video showing Raspberry pi running the screen test:**



https://github.com/user-attachments/assets/cbe5903a-3aeb-4574-a041-5d257a882573


<br><br>

#### Displaying an image

Next, We ran `image.py` to display a picture. we copied our own picture, `earthing.jpg`, from my laptop to the `Lab 2` folder on the Pi. The program resized and cropped the picture to fit the small display.

We modified `image.py` to switch between two pictures using the buttons. Button A displays `red.jpg`, and button B displays `earthing.jpg`. **earthing.jpg is uploaded inside lab 2.** We used a `while True` loop to keep checking the buttons and a variable to remember which picture was selected. The selected picture stays on the screen after the button is released. **Modified image.py is named "Modified_image.py" and is uploaded inside Lab 2.**

I also changed the display’s reset setting to `None`, allowing GPIO24 to be used as the input for button B. We tested switching between the pictures and recorded a video showing the interaction.


**Image showing the image:**


<img width="1600" height="1200" alt="Imgae py" src="https://github.com/user-attachments/assets/7ea66250-1cce-410b-8c64-b98341579227" />

<br><br>

**Video showing the buttons switching between two pictures:**




https://github.com/user-attachments/assets/d7a301a1-a5b7-4e5f-b39e-851d14ac3355


<br><br>


\*\*\***Include a picture of your own Raspberry Pi displaying the piscreen.service with your unique MAC address. Additionally, please provide another picture showing the successful completion of the screen test.**\*\*\*


## Part D. 
### Set up the Display Clock Demo

For this part, we completed the missing section of `screen_clock.py` to display the current date and time on the MiniPiTFT screen.

We edited the file through PuTTY using `nano screen_clock.py`. Initially, the program displayed only a red background because the `while True` loop did not contain any instructions to draw the time. We replaced the TODO section with the clock instructions and changed the background to black.

We used `cli_clock.py` as a reference for getting the current date and time with `time.strftime()`. The format `%m/%d/%Y %H:%M:%S` displays the month, day, year, and time in a 24-hour format. We used `stats.py` as a reference for drawing text with `draw.text()`.

Inside the loop, the program clears the previous image, gets the current date and time, and draws it in white. It then sends the image to the display using `disp.image()`. The `time.sleep(1)` instruction makes the program wait one second before repeating these steps.

After editing, We saved the file using Ctrl+O, pressed Enter, and exited nano using Ctrl+X. We stopped `piscreen.service` so the clock program could use the screen, then ran `python screen_clock.py`. **Modified screen_clock.py is named "Modified_screen_clock.py" and is uploaded inside Lab 2.** 
The display showed the date and time on a black background, with the seconds updating continuously. We could stop the program by pressing Ctrl+C in PuTTY.

**Raspberry pi display showing the date and time:**

<img width="4032" height="3024" alt="Pi Clock vs Real Clock" src="https://github.com/user-attachments/assets/6c608e7f-463b-4340-85cf-0ad9806ad29c" />


https://github.com/user-attachments/assets/ea6c690b-4be8-4c24-ba1b-7063ad555e65




## Part E. Read Part 2. Sketch and brainstorm further interactions and features you would like for your clock.

** Insert ideas, sketches, [Verplank diagrams](https://ccrma.stanford.edu/courses/250a-fall-2004/IDSketchbok.pdf)), storyboards for your ideas **

**Sketch 1:**
Our first (and favorite) idea is the  Flower Clock is a timekeeping concept that uses the natural blooming cycles of flowers to represent time. Since flowers open and close their petals according to their internal circadian rhythms, different species can bloom at different times of day. By observing three different flower cycles, we can represent seconds, minutes, and hours, creating a clock that connects the passage of time with the rhythms of nature.


<img width="526" height="598" alt="Screenshot 2026-09-13 at 1 49 46 PM" src="https://github.com/user-attachments/assets/ff912314-9dca-43a2-8978-98f6b010a333" />


**Sketch 2:**
The Abacus Clock is a timekeeping concept inspired by the ancient abacus, a counting tool used for arithmetic and trade. Abacuses have been used for thousands of years, with early counting devices emerging in ancient civilizations such as Mesopotamia, while the Chinese suanpan later became one of the most well-known forms. This clock uses sliding beads to represent the hours, minutes, and seconds of the day. As time progresses, the beads move upward from the lower deck toward the upper deck, creating a visual representation of the passage of time. By combining the familiar counting system of the abacus with timekeeping, this design transforms a historical mathematical tool into a modern clock.


<img width="522" height="539" alt="Screenshot 2026-09-13 at 1 50 04 PM" src="https://github.com/user-attachments/assets/31de9019-f3b4-41d3-b25e-b0d6e423214f" />


**Sketch 3:**
Lastly, our Checklist Clock is a timekeeping concept inspired by the daily checklists and routines we use to organize our lives. Instead of displaying time through traditional numbers or hands, it represents the progression of the day through tasks and activities, such as classes, meals, and studying. To make the clock more interactive, we propose using an ESP32, microphone, and speaker with voice recognition, allowing users to ask for the time and receive spoken reminders about upcoming tasks. This transforms a traditional clock into a personalized, voice-controlled daily planner.


<img width="525" height="568" alt="Screenshot 2026-09-13 at 1 50 23 PM" src="https://github.com/user-attachments/assets/42a217eb-a65c-46c1-a481-fc4cfcc35e24" />


**Put the names of the people you gave feedback to here. (Even better, add links to their repos here!)**

# Lab 2 Part 2

## Prep 

**Feedback from Jindi chai & Yilin Wu:** I liked all three ideas. My favorite is the Flower Clock. It can tell time, but it can also be a nice decoration for a room. It feels peaceful and connected to nature. I like growing plants at home, but real plants can be hard to take care of. This idea makes plants digital, but they still have a useful purpose. Your sketches are clear and easy to understand.
One suggestion is to let users choose their own flowers and colors. They could make a flower clock with their favorite flower combination. It may also be helpful to add a small digital time display, so users can quickly check the exact time.
[View their project ↗](https://github.com/yw2895-ship-it/Interactive-Lab-Hub/blob/Fall2026/Lab%202/README.md)

**Feedback from Sirapop Umnakkittikul:** I think the third sketch is a really cool idea. I like how it turns a traditional clock into something more personal by representing the day through tasks and routines instead of just numbers. Using an ESP32 with a microphone and speaker for voice control is a smart approach, and combining it with an LLM could make the interaction feel more natural and users could ask for the time and get spoken reminders about upcoming tasks. It effectively transforms the clock into a personalized, voice-controlled daily planner, which feels both practical and innovative.
[View their project ↗](https://github.com/Morinzzz/Interactive-Lab-Hub/tree/Fall2026/Lab%202)

**Feedback :** Lovely drawings! We shared similar ideas about the flower clock hh. I like your flower clock very much because I think it's a beautiful and clear visualization of hour, minutes and seconds. And the process of flower blossom is a symbol of time already, so it's an interesting metaphor. Maybe you can think about adding something to tell the difference between a.m and p.m.? And another thing about the motion, are you going to make 60 states, 60 pictures for each flower to show every exact seconds? Or how are you gonna divide? It's a practical question for prototyping. [View their project ↗]()


\*\*\***Put a copy of your code in your Lab 2 Github repo.**\*\*\*

## Make a short video of your modified barebones PiClock

\*\*\***Take a video of your barely modified PiClock.**\*\*\*

After you edit and work on the scripts for Lab 2, the files should be upload back to your own GitHub repo! You can push to your personal github repo by adding the files here, commiting and pushing.

```
(venv) pi@raspberrypi:~/Interactive-Lab-Hub/Lab 2 $ git add .
(venv) pi@raspberrypi:~/Interactive-Lab-Hub/Lab 2 $ git commit -m 'your commit message here'
(venv) pi@raspberrypi:~/Interactive-Lab-Hub/Lab 2 $ git push
```

After that, Git will ask you to login to your GitHub account to push the updates online, you will be asked to provide your GitHub user name and password. Remember to use the "Personal Access Tokens" you set up in Part A as the password instead of your account one! Go on your GitHub repo with your laptop, you should be able to see the updated files from your Pi!

## Now, make your own PiClock

Do take advantage of having done the previous iteration to refine and simplify your design.

** Insert any updates ideas, sketches, [Verplank diagrams](https://ccrma.stanford.edu/courses/250a-fall-2004/IDSketchbok.pdf))!, storyboards for your ideas **


**Final Clock Direction**

After discussing the three concepts and receiving feedback, we decided to move forward with our **Flower Clock** idea because we liked how it combines timekeeping with a natural, interactive visual.

**1. Second Clock**

The seconds flower blooms continuously over each 60-second minute, with the closed bud at :00, opening in real time petal by petal, and reaching full bloom right at :59 before resetting. A new leaf sprouts every 15 seconds as it grows. It's a blue, tulip-style bloom with 8 rounded petals, redrawn ~15 times a second so the motion looks smoother to the user, rather than ticking in discrete steps.

**2. Minute Clock**

For the minute portion of the flower clock, we designed a 12-petal flower, with each petal representing a 5-minute interval. A butterfly moves clockwise around the flower to show the current minute, moving smoothly between petals using the current seconds as well. Then, we refined the flower by making the petals narrower and more evenly spaced, so all 12 petals are clearly visible instead of overlapping. During the daytime, the butterfly moves around the flower, and at night it changes into a glowing firefly to match the time of day.

**3. Hour Clock**

We also built an Hour Flower feature: a 12-petal sunflower with large, rounded golden-orange petals and a classic brown seeded center, set against a solid black background. As the hours pass, one petal falls at a time, with the flower reaching full bloom at both midnight and noon. To make the passage of time more visually engaging, every four seconds, a large visible chunk breaks off the current hour’s petal, gradually shrinking as it falls before merging into the small pile growing on the ground. Additionally, the petal on the flower itself visibly shrinks approximately every six minutes, making the progression easy to notice at a glance. Meanwhile, a small sun arcs across the sky from 5 AM to 8 PM, transitioning into a crescent moon throughout the night. Finally, the bottom of the display shows the live time, a percentage counting down to the next petal fall, and “X petal fell,” which corresponds to the current 12-hour clock digit.


\*\*\***Put a copy of your code in your Lab 2 Github repo.**\*\*\*

\*\*\***Video**\*\*\*


https://github.com/user-attachments/assets/52ec7c64-2cd9-4ca7-b5a2-9426050400ad

