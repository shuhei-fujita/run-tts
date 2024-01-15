# 複数のクラスを持つ要素を選択
const activeTabContents = document.querySelectorAll('.contents__tabContents.js-tabContents.is-active');

// 選択された各要素のテキスト内容を改行で区切って表示
activeTabContents.forEach((content, index) => {
    const divs = content.querySelectorAll('div');
    let textOutput = `タブ ${index + 1}:\n`;

    divs.forEach(div => {
        textOutput += div.innerText + '\n';
    });

    console.log(textOutput);
});
