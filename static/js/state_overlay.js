let streamState = null;
const WAIT_TIME = 8000;
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
    let container = document.getElementById("stateContainer");
    let image = document.createElement("img");
    image.src = img;
    if (data === "NonEssentialFish") {
        image.classList.add("fish");
    }

    container.classList.add(ANIM_IN);

    container.appendChild(image);
    container.insertAdjacentText("beforeend", data);

    await sleep(WAIT_TIME);

    container.classList.remove(ANIM_IN);
    container.classList.add(ANIM_OUT);

    await sleep(ANIM_SPEED);

    container.removeChild(image);
    container.innerText = "";

    container.classList.remove(ANIM_OUT);
}

async function overlayLoop() {
    let count = 0;
    let first;
    let follower;
    let subscriber;

    while (true) {
        if (count % 2 === 0) {
            await updateState();
        }

        follower = streamState["follower"];
        subscriber = streamState["subscriber"];
        first = streamState["first"];

        await transition(first, "/static/images/cat_hype.png");
        await transition(follower, "/static/images/cat_love.png");
        await transition(subscriber, "/static/images/cat_star.png");
        await transition("NonEssentialFish", "/static/images/fish.png");

        count++;
    }
}