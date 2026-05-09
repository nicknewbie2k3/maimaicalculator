const slideNodeSequence = {
    straightLine: [ // - symbol
        null, // 0/8 dist has no line
        null, // 1 dist has no line
        [     // 2 dist (e.g. from 1 to 3)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }, { group: "b", id: 2 }], //a2 or b2
            [{ group: "a", id: 3 }]
        ],
        [     // 3 dist (e.g. from 1 to 4)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "a", id: 4 }] //a4
        ],
        [     // 4 dist (e.g. from 1 to 5)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 5 }] //a5
        ],
        [     // 5 dist (e.g. from 1 to 6)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b1
            [{ group: "b", id: 7 }], //b5
            [{ group: "a", id: 6 }] //a6
        ],
        [     // 6 dist (e.g. from 1 to 7)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }, { group: "b", id: 8 }], //a8 or b8
            [{ group: "a", id: 7 }] //a7
        ],
        null // 7 dist has no line
    ],
    circumferenceCW: [ // > symbol
        [ // 0/8 dist is a full loop
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 1 }] //a1
        ],
        [ // 1 dist (e.g. from 1 to 2)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }] //a2
        ],
        [ // 2 dist (e.g. from 1 to 3)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }] //a3
        ],
        [ // 3 dist (e.g. from 1 to 4)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 4 }] //a4
        ],
        [ // 4
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 5 }] //a5
        ],
        [ // 5
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 6 }] //a6
        ],
        [ // 6
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 7 }] //a7
        ],
        [ // 7
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }] //a8
        ]
    ],
    circumferenceCCW: [ // < symbol
        [ // 0/8 dist is a full loop
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 1 }] //a1
        ],
        [ // 1 dist (e.g. from 1 to 2)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }] //a2
        ],
        [ // 2 dist (e.g. from 1 to 3)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 4 }], //a4
            [{ group: "a", id: 3 }] //a3
        ],
        [ // 3 dist (e.g. from 1 to 4)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 5 }], //a5
            [{ group: "a", id: 4 }] //a4
        ],
        [ // 4 dist (e.g. from 1 to 5)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 6 }], //a6
            [{ group: "a", id: 5 }] //a5
        ],
        [ // 5 dist (e.g. from 1 to 6)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 6 }] //a6
        ],
        [ // 6 dist (e.g. from 1 to 7)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 7 }] //a7
        ],
        [ // 7 dist (e.g. from 1 to 8)
            [{ group: "a", id: 1 }], //a1
            [{ group: "a", id: 8 }] //a8
        ]
    ],
    arcAlongCenterCW: [ // p symbol
        [ // 0/8 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 8 }], //b8
            [{ group: "a", id: 1 }] //a1
        ],
        [ // 1 dist (e.g. from 1 to 2)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 1 }], //b1
            [{ group: "a", id: 2 }] //a2
        ],
        [ // 2 dist (e.g. from 1 to 3)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 2 }], //b2
            [{ group: "a", id: 3 }] //a3
        ],
        [ // 3 dist (e.g. from 1 to 4)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "a", id: 4 }] //a4
        ],
        [ // 4 dist (e.g. from 1 to 5)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 5 }] //a5
        ],
        [ // 5 dist (e.g. from 1 to 6)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 6 }] //a6
        ],
        [ // 6 dist (e.g. from 1 to 7)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }] //a7
        ],
        [ // 7 dist (e.g. from 1 to 8)
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 7 }], //b7
            [{ group: "a", id: 8 }] //a8
        ],
    ],
    arcAlongCenterCCW: [ // q symbol
        [ // 0/8 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 2 }], //b2
            [{ group: "a", id: 1 }] //a1
        ],
        [ // 1 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 3 }], //b3
            [{ group: "a", id: 2 }] //a2
        ],
        [ // 2 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }] //a3
        ],
        [ // 3 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 4 }] //a4
        ],
        [ // 4 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 5 }] //a5
        ],
        [ // 5 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "a", id: 6 }] //a6
        ],
        [ // 6 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 8 }], //b8
            [{ group: "a", id: 7 }] //a7
        ],
        [ // 7 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "b", id: 5 }], //b5
            [{ group: "b", id: 4 }], //b4
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 1 }], //b1
            [{ group: "a", id: 8 }] //a8
        ]
    ],
    zigzagS: [ // s symbol
        null, // only 4 dist
        null, // only 4 dist
        null, // only 4 dist
        null, // only 4 dist
        [ //4 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 3 }], //b3
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 5 }] //a5
        ],
        null, // only 4 dist
        null, // only 4 dist
        null // only 4 dist
    ],
    zigzagZ: [ // z symbol
        null, // only 4 dist
        null, // only 4 dist
        null, // only 4 dist
        null, // only 4 dist
        [ //4 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 7 }], //b7
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 5 }] //a5
        ],
        null, // only 4 dist
        null, // only 4 dist
        null // only 4 dist
    ],
    centerBounce: [ // v symbol
        null, // 0/8 dist cant make a line to itself
        [ //1 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 2 }], //b2
            [{ group: "a", id: 2 }] //a2
        ],
        [ //2 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 3 }], //b3
            [{ group: "a", id: 3 }] //a3
        ],
        [ //3 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 4 }] //a4
        ],
        [ // 4 dist would just be straight line
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 5 }] //a5
        ],
        [ //5 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 6 }] //a6
        ],
        [ //6 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 7 }], //b7
            [{ group: "a", id: 7 }] //a7
        ],
        [ //7 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 8 }], //b8
            [{ group: "a", id: 8 }] //a8
        ]
    ],
    arcToSideCW: [ // pp symbol
        [ // 0/8 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 1 }] //a1
        ],
        [ // 1 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "a", id: 1 }, { group: "b", id: 1 }], //a1 or b1
            [{ group: "a", id: 2 }] //a2
        ],
        [ // 2 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 2 }], //b2
            [{ group: "a", id: 3 }], //a3
        ],
        [ // 3 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 2 }, { group: "c", id: 1 }, { group: "c", id: 2 }], //b2 or c1 or c2
            [{ group: "b", id: 3 }, { group: "b", id: 4 }], //b3 or b4
            [{ group: "a", id: 4 }], //a4
        ],
        [ // 4 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 5 }], //a5
        ],
        [ // 5 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 6 }], //a6
        ],
        [ // 6 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
        ],
        [ // 7 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 6 }], //b6
            [{ group: "a", id: 7 }], //a7
            [{ group: "a", id: 8 }], //a8
        ]
    ],
    arcToSideCCW: [ // qq symbol
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 1 }], //a1
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 4 }], //a4
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 5 }], //a5
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 8 }, { group: "c", id: 1 }, { group: "c", id: 2 }], //b8 or c1 or c2
            [{ group: "b", id: 7 }, { group: "b", id: 6 }], //b7 or b6
            [{ group: "a", id: 6 }], //a6
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "b", id: 1 }], //b1
            [{ group: "b", id: 8 }], //b8
            [{ group: "a", id: 7 }], //a7
        ],
        [
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 4 }], //b4
            [{ group: "a", id: 3 }], //a3
            [{ group: "a", id: 2 }], //a2
            [{ group: "a", id: 1 }, { group: "b", id: 1 }], //a1 or b1
            [{ group: "a", id: 8 }], //a8
        ]
    ],
    fanSegments: [ // w symbol
        null, // 0/8 dist
        null, // 1 dist
        null, // 2 dist
        [ // 3 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 8 }], //b8
            [{ group: "b", id: 7 }], //b7
            [{ group: "a", id: 6 }, { group: "d", id: 6 }], //a6 or d6
        ],
        [ // 4 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 1 }], //b1
            [{ group: "c", id: 1 }, { group: "c", id: 2 }], //c1 or c2
            [{ group: "b", id: 5 }], //b5
            [{ group: "a", id: 5 }], //a5
        ],
        [ // 5 dist
            [{ group: "a", id: 1 }], //a1
            [{ group: "b", id: 2 }], //b2
            [{ group: "b", id: 3 }], //b3
            [{ group: "a", id: 4 }, { group: "d", id: 5 }], //a4 or d5
        ],
        null, // 6 dist
        null, // 7 dist
        null // 8 dist
    ]
}