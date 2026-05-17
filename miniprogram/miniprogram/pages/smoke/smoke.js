function checkApiAvailability() {
  return [
    {
      id: 'random',
      label: 'wx.getRandomValues',
      available: typeof wx.getRandomValues === 'function',
    },
    {
      id: 'storage',
      label: 'wx.setStorage / wx.getStorage',
      available:
        typeof wx.setStorage === 'function' && typeof wx.getStorage === 'function',
    },
    {
      id: 'scan',
      label: 'wx.scanCode',
      available: typeof wx.scanCode === 'function',
    },
  ]
}

function loadCryptoSubpackage() {
  return new Promise((resolve, reject) => {
    wx.loadSubpackage({
      name: 'crypto',
      success: resolve,
      fail: reject,
    })
  })
}

function createPendingSuite() {
  return [
    { id: 'x25519', label: 'X25519 + HKDF-SHA256', status: 'pending', message: '等待执行' },
    { id: 'aead', label: 'XChaCha20-Poly1305 AEAD', status: 'pending', message: '等待执行' },
    { id: 'argon2id', label: 'Argon2id (t=3, m=64MB)', status: 'pending', message: '等待执行' },
  ]
}

Page({
  data: {
    loading: false,
    subpackageReady: false,
    suite: createPendingSuite(),
    apiChecks: checkApiAvailability(),
    lastRunAt: '',
    failureMessage: '',
  },

  onLoad() {
    this.runSmoke()
  },

  async runSmoke() {
    this.setData({
      loading: true,
      subpackageReady: false,
      failureMessage: '',
      suite: createPendingSuite(),
      apiChecks: checkApiAvailability(),
    })

    try {
      await loadCryptoSubpackage()
      const { runCryptoSmokeTests } = require('../../subpackages/crypto/index.js')
      const suite = await runCryptoSmokeTests()

      this.setData({
        loading: false,
        subpackageReady: true,
        suite,
        lastRunAt: new Date().toLocaleString(),
      })
    } catch (error) {
      const message =
        error && error.message ? error.message : String(error || '未知错误')

      this.setData({
        loading: false,
        subpackageReady: false,
        failureMessage: message,
        suite: createPendingSuite().map((item) => ({
          ...item,
          status: 'failed',
          message: message,
        })),
      })
    }
  },
})
