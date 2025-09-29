let tick = 0;

let config = {
    type: Phaser.AUTO,
    width: 1920,
    height: 900,
    scene: {
        preload: preload,
        create: create,
        update: update
    },
    transparent: true,
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 300 },
            debug: false
        }
    },
};

var game = new Phaser.Game(config);

function preload() {
    this.load.spritesheet("CHICKEN", "/static/images/chickens/chicken_walk.png", { frameWidth: 32, frameHeight: 32 });
}

function create() {
    npc = this.physics.add.sprite(100, 450, "CHICKEN").setScale(2).refreshBody();
    npc.setCollideWorldBounds(true);

    ground = this.physics.add.staticImage(1920 / 2, 16, null); // No texture key
    ground.setSize(1920, 32);

    myText = this.add.text(npc.x, npc.y, 'MystyPy', { 
        font: '16px Arial', 
        fill: '#000' 
    });

    this.anims.create({
        key: "WALK",
        frames: this.anims.generateFrameNumbers("CHICKEN", { start: 0, end: 3 }),
        frameRate: 10,
        repeat: -1
    });
    this.anims.create({
        key: "IDLE",
        frames: [{ key: "CHICKEN", frame: 0 }],
        frameRate: 20
    });

    timer = this.time.addEvent({
        delay: Phaser.Math.Between(1000, 3000), // ms
        callback: runChicken,
        args: [],
        loop: true,
        repeat: -1,
        startAt: 0,
        timeScale: 1,
        paused: false,
        callbackScope: this,
    });
}

function runChicken() {
    let DIR = ["LEFT", "IDLE", "RIGHT"];
    let randDir = DIR[Phaser.Math.Between(0, DIR.length - 1)];

    switch (randDir) {
        case "LEFT":
            npc.setFlipX(false);
            npc.setVelocityX(160);
            npc.anims.play("WALK", true);
            break;
        case "IDLE":
            npc.setVelocityX(0);
            npc.anims.play("IDLE", true);
            break;
        case "RIGHT":
            npc.setFlipX(true);
            npc.setVelocityX(-160);
            npc.anims.play("WALK", true);
    }
}

function update() {
    myText.setPosition(npc.x + -32, npc.y + -48); 
}