let streamState = null;

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

async function updateAnimals(chatters) {
    let src = "/static/images/cat_hype.png";  // TODO: Random animal?
    let container = document.getElementById("birdContainer");


    for (let chatter of chatters) {
        let img = document.createElement("img");
        img.src = src;

        let inner = document.createElement("div");
        inner.classList.add("wot")

        inner.insertAdjacentText("afterbegin", Object.keys(chatter)[0]);
        inner.insertAdjacentElement("beforeEnd", img);
        container.insertAdjacentElement("beforeEnd", inner);
    }
}

async function overlayLoop() {
    await updateState();

    while (true) {
        await sleep(4000);

        let chatters = streamState.chatter_cache;
        if (!chatters) { continue }

        await updateAnimals(chatters);
    }
}
