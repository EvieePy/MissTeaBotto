const eventSource = new EventSource("/sse/alerts");


eventSource.onmessage = async (message) => {
    const event = JSON.parse(message.data);
    const data = event.data;
    const wait = event.duration;

    await processEvent(data, wait);
};

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function stopAudio(audio) {
    audio.pause();
    audio.currentTime = 0;
    audio.src = "";
}

async function processEvent(data, wait) {
    const imgSrc = data.image;
    const audioSrc = data.audio;
    const text = data.text;

    const audio = new Audio(audioSrc);
    audio.volume = 0.4;

    const image = document.createElement("img");
    image.src = imgSrc;

    const container = document.getElementById("alertContainer");
    container.insertAdjacentElement("afterbegin", image);
    container.insertAdjacentText("beforeend", text || "");

    audio.play();

    await sleep((wait - 1) * 1000);
    stopAudio(audio);
    container.innerHTML = "";
}