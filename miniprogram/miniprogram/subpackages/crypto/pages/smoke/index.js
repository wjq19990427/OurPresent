function checkApiAvailability() {
  const randomAvailable = typeof wx.getRandomValues === 'function'
  const storageAvailable =
    typeof wx.setStorage === 'function' && typeof wx.getStorage === 'function'
  const scanAvailable = typeof wx.scanCode === 'function'

  return [
    {
      id: 'random',
      label: 'wx.getRandomValues',
      available: randomAvailable,
      availabilityText: randomAvailable ? 'available' : 'unavailable',
      availabilityClass: randomAvailable ? 'ok' : 'bad',
    },
    {
      id: 'storage',
      label: 'wx.setStorage / wx.getStorage',
      available: storageAvailable,
      availabilityText: storageAvailable ? 'available' : 'unavailable',
      availabilityClass: storageAvailable ? 'ok' : 'bad',
    },
    {
      id: 'scan',
      label: 'wx.scanCode',
      available: scanAvailable,
      availabilityText: scanAvailable ? 'available' : 'unavailable',
      availabilityClass: scanAvailable ? 'ok' : 'bad',
    },
  ]
}

function createPendingSuite() {
  return [
    {
      id: 'x25519',
      label: 'X25519 + HKDF-SHA256',
      status: 'pending',
      statusText: '等待',
      statusClass: 'pending',
      message: '等待执行',
    },
    {
      id: 'aead',
      label: 'XChaCha20-Poly1305 AEAD',
      status: 'pending',
      statusText: '等待',
      statusClass: 'pending',
      message: '等待执行',
    },
    {
      id: 'argon2id',
      label: 'Argon2id (t=3, m=64MB)',
      status: 'pending',
      statusText: '等待',
      statusClass: 'pending',
      message: '等待执行',
    },
  ]
}

function decorateSuite(suite) {
  return suite.map((item) => {
    if (item.status === 'passed') {
      return {
        ...item,
        statusText: '通过',
        statusClass: 'passed',
      }
    }

    if (item.status === 'failed') {
      return {
        ...item,
        statusText: '失败',
        statusClass: 'failed',
      }
    }

    return {
      ...item,
      statusText: '等待',
      statusClass: 'pending',
    }
  })
}

Page({
  data: {
    loading: false,
    suite: createPendingSuite(),
    apiChecks: checkApiAvailability(),
    lastRunAt: '',
    failureMessage: '',
    rerunButtonText: '重新运行',
    subpackageStatusText: 'ready',
    subpackageDetail: 'crypto smoke page is running inside the crypto subpackage',
  },

  onLoad() {
    this.runSmoke()
  },

  async runSmoke() {
    this.setData({
      loading: true,
      failureMessage: '',
      suite: createPendingSuite(),
      apiChecks: checkApiAvailability(),
      rerunButtonText: '测试中...',
      subpackageStatusText: 'ready',
      subpackageDetail: 'crypto smoke page is running inside the crypto subpackage',
    })

    try {
      const { runCryptoSmokeTests } = require('../../index.js')
      const suite = decorateSuite(await runCryptoSmokeTests())

      this.setData({
        loading: false,
        suite,
        lastRunAt: new Date().toLocaleString(),
        rerunButtonText: '重新运行',
      })
    } catch (error) {
      const message =
        error && error.message ? error.message : String(error || '未知错误')

      this.setData({
        loading: false,
        failureMessage: message,
        suite: decorateSuite(
          createPendingSuite().map((item) => ({
            ...item,
            status: 'failed',
            message: message,
          }))
        ),
        rerunButtonText: '重新运行',
      })
    }
  },
})
