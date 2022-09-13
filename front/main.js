const {app, BrowserWindow} = require('electron');
const axios = require('axios').default

function createWindow() {
    const mainWindow = new BrowserWindow({
        width: 800,
        height:600,
        title: "BeAssist",
        icon: "../static/assets/img/logos/android-chrome-192x192.png"
    })
    try {
        mainWindow.loadURL('http://127.0.0.1:8000/')
    } catch (error) {
        mainWindow.loadFile('../templates/404.html')
    }

    app.on('window-all-closed', () => {
        console.log('Application en cours de fermeture ...')
        axios
            .post('http://127.0.0.1:8000/shutdown')
            .then(res => console.log(res.data.message))
            .catch(err => console.log(err.message))
        app.quit()
    })
}

app.whenReady().then(() => createWindow())
