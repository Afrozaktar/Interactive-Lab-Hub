# Interactive Prototyping: The Clock of Pi
**NAMES OF COLLABORATORS: Afroza Aktar, KM, Lamiah Khan

**Please indicate anyone you collaborated with on this Lab here.**
Be generous in acknowledging their contributions! And also recognizing any other influences (e.g. from YouTube, Github, Twitter) that informed your design. 

***Update your [parts list inventory](partslist.md)***

## The Report
This readme.md page in your own repository should be edited to include the work you have done. You can delete everything but the headers and the sections between the \*\*\***stars**\*\*\*. Write the answers to the questions under the starred sentences. Include any material that explains what you did in this lab hub folder, and link it in the readme.

Labs are due on Sunday midnight. Make sure this page is linked to on your main class hub page.

## Part A. 
### Connect to your Pi

We connected to Raspberry Pi from laptop using PuTTY and SSH. We entered the Pi’s IP address and logged in with username and password. This allowed us to run commands on the Pi remotely.

[Image of terminal showing rpi connected]


## Part B. 
### Try out the Command Line Clock

We cloned `Interactive-Lab-Hub` GitHub repository onto the Raspberry Pi. 
With the virtual environment active, I installed the required Python packages using `pip install -r requirements.txt`. I then ran the command-line clock with `python cli_clock.py`.

The program displayed the current date and time in the PuTTY terminal. The time updated every second on the same line. 

[ screenshot or video link showing the command-line clock running in PuTTY.]

## Part C. 
### Set up your RGB Display
For this part, we used the Adafruit MiniPiTFT display connected to my Raspberry Pi 5. The display communicates with the Pi using SPI. GPIO23 and GPIO24 connect to the two buttons, and GPIO22 controls the display’s backlight.

#### Displaying Info with Texts

We ran `piscreen.service` to display information about my Raspberry Pi, including its IP address, MAC address, memory usage, and CPU temperature. We also looked at `screen_boot_script.py` to understand how text is displayed. The program uses `draw.text()` to write information onto an image and `disp.image()` to show that image on the physical screen.

[Photo 1: Raspberry Pi displaying the system information, with unique MAC address]

Before running the other display programs, We stopped the startup service using `sudo systemctl stop piscreen.service`. This allowed the test program to use the display without another program trying to control the same pins.

### Testing your Screen

We then ran `python screen_test.py`, entered a color name red, and tested the buttons. With neither button pressed, the screen displayed green. Pressing button A displayed white, while pressing button B displayed red color. Pressing both buttons turned off the backlight. This showed that the display, buttons, and backlight responded to the program.

[Insert Photo Raspberry Pi successfully running the screen test.]

[screen-test video link here.]

#### Displaying an image

Next, We ran `image.py` to display a picture. we copied our own picture, `earthing.jpg`, from my laptop to the `Lab 2` folder on the Pi. The program resized and cropped the picture to fit the small display.

We modified `image.py` to switch between two pictures using the buttons. Button A displays `red.jpg`, and button B displays `earthing.jpg`. We used a `while True` loop to keep checking the buttons and a variable to remember which picture was selected. The selected picture stays on the screen after the button is released. Modified image.py is named "Modified_image.py" and is uploaded inside Lab 2. 

I also changed the display’s reset setting to `None`, allowing GPIO24 to be used as the input for button B. I tested switching between the pictures and recorded a video showing the interaction.

[video showing button presses switching between the two pictures.]

\*\*\***Include a picture of your own Raspberry Pi displaying the piscreen.service with your unique MAC address. Additionally, please provide another picture showing the successful completion of the screen test.**\*\*\*


## Part D. 
### Set up the Display Clock Demo

For this part, we completed the missing section of `screen_clock.py` to display the current date and time on the MiniPiTFT screen.

We edited the file through PuTTY using `nano screen_clock.py`. Initially, the program displayed only a red background because the `while True` loop did not contain any instructions to draw the time. We replaced the TODO section with the clock instructions and changed the background to black.

We used `cli_clock.py` as a reference for getting the current date and time with `time.strftime()`. The format `%m/%d/%Y %H:%M:%S` displays the month, day, year, and time in a 24-hour format. We used `stats.py` as a reference for drawing text with `draw.text()`.

Inside the loop, the program clears the previous image, gets the current date and time, and draws it in white. It then sends the image to the display using `disp.image()`. The `time.sleep(1)` instruction makes the program wait one second before repeating these steps.

After editing, We saved the file using Ctrl+O, pressed Enter, and exited nano using Ctrl+X. We stopped `piscreen.service` so the clock program could use the screen, then ran `python screen_clock.py`.

The display showed the date and time on a black background, with the seconds updating continuously. We could stop the program by pressing Ctrl+C in PuTTY.

[photo of our Raspberry Pi displaying the working clock.]

[video link showing the seconds changing.]


## Part E. Read Part 2. Sketch and brainstorm further interactions and features you would like for your clock.

One potential source of ideas might be thinking about other clocks and timekeeping devices for inspiration.

Another might be novel units of time. How do you measure a year? [In daylights? In midnights? In cups of coffee?](https://www.youtube.com/watch?v=wsj15wPpjLY)

We strongly discourage literal digital or analog clock display: Be creative.


** Insert ideas, sketches, [Verplank diagrams](https://ccrma.stanford.edu/courses/250a-fall-2004/IDSketchbok.pdf)), storyboards for your ideas **



**Put the names of the people you gave feedback to here. (Even better, add links to their repos here!)**

# Lab 2 Part 2

## Prep 

1. Pick up remaining parts for kit on Wednesday lab class. Check the updated [parts list inventory](partslist.md) and let the TA know if there is any part missing.

2. Look at and give feedback on the Part E. for at least 3 other people in the class and get 3 people to comment on your Part E!)
**Put the feedback for your ideas here.**

## Update your Lab Hub

[Update your Lab Hub](pull_updates/README.md) to get the latest content and requirements for Part 2.

## Modify the barebones clock to make it your own

Start small, pick just one element of your overall idea, just to show you have a handle on the code and components.

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


\*\*\***Put a copy of your code in your Lab 2 Github repo.**\*\*\*

\*\*\***Take a video of your PiClock.**\*\*\*


As always, make sure you document contributions and ideas from others (and AI) explicitly in your writeup.

You are permitted (but not required) to work in groups and share a turn in; you are expected to make equal contribution on any group work you do, and N people's group project should look like N times the work of a single person's lab.  Make sure the page for the group turn in is linked to your personal Interactive Lab Hub page. 


