let streamState = null;
let previous = null;
const WAIT_TIME = 5000;
const ANIM_SPEED = 800;

const ANIM_IN = "animate__fadeIn";
const ANIM_OUT = "animate__fadeOut"


document.addEventListener("DOMContentLoaded", async () => {
    await overlayLoop();
});


async function updateState() {
    let resp;

    try {
        resp = await fetch("/data/stream_state");
    } catch (error) {
        console.log(`An error occurred fetching stream state: ${error}`);
        return;
    }

    streamState = await resp.json();
    console.log("Updated Stream State");
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function transition(data, img) {
    let container = document.getElementById("songContainer");
    let songContainer = document.getElementById("song");
    let image = document.getElementById("songImg");

    // Remove Previous Song...
    container.classList.remove(ANIM_IN);
    container.classList.add(ANIM_OUT);

    await sleep(ANIM_SPEED);

    // Add new Song...
    songContainer.innerText = data;
    image.src = img;

    await sleep(100);
    container.classList.remove(ANIM_OUT);
    container.classList.add(ANIM_IN);
}

async function overlayLoop() {
    while (true) {
        await sleep(WAIT_TIME);
        await updateState();

        if (!streamState) {
            continue;
        }

        if (!previous) {
            previous = streamState;
            if (previous) {
                await transition(streamState.playing.title, streamState.playing.image);
            }

            continue;
        }

        if (previous.playing.title === streamState.playing.title) {
            continue;
        }

        previous = streamState;
        await transition(streamState.playing.title, streamState.playing.image);
    }
}