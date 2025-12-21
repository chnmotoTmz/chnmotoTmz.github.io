PS C:\Users\motoc\gemini-api-wrapper> Invoke-RestMethod -Uri 'http://localhost:3000/api/request_cookies' `
>>   -Method Post `
>>   -ContentType 'application/json' `
>>   -Body '{"url":"https://gemini.google.com/","names":["__Secure-1PSID"]}' | ConvertTo-Json -Depth 5               
{
  "success": true,
  "cookies": [
    {
      "name": "COMPASS",
      "value": "gemini-pd=CjwACWuJV93jFYb_b6k1ZbZc5AVi75OXfwVJx6huPFdJgLZgT-iphNSBtyIyTho-2Gurv4U86El7hPmdVFUQyO6KygYaXQAJa4lXn9oi4Cbh75qeYR3VIE0BY5djWcUkAbEEzbhIu_LGieSlhyOewtmGSBpTT7Xb-poYs9ewAACTB5-VRmbP3P-ekagH_KMx5nISDa6_Ics_JeT9RdVB0hIHdSABMAE:gemini-hl=CkkACWuJV4Jq7gXnYGXm-CCWRGf1MNczIJ0yMsen8R98zb0fdd_v1HDcw_-Y0Gxw7WZu_GGVl89NUAGecp6EG6tM_DjudIlkdiK-ELfajMoGGmoACWuJV5CQ8pDAP50ezEOaV4OgrHoHttckpmemYdK1_oPE7fq21bvGOIBSxDUuDIlvAqiQIPlMfqXWkIDETvz2JlDdNgpTCCYe3tRksOoygjScyo251yEhQOJ4r8-frfSVO-h9Z-kSna0rIAEwAQ",
      "domain": "gemini.google.com"
    }
  ]
}
PS C:\Users\motoc\gemini-api-wrapper> Invoke-RestMethod -Uri 'http://localhost:3000/api/cookies?domain=googleusercontent.com' -Method Get | ConvertTo-Json -Depth 5               
{
  "success": true,
  "cookies": {
    "google.com": [
      {
        "name": "__Secure-BUCKET",
        "value": "CJ4D",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PSID",
        "value": "g.a0004giE9A7E6ZsKFEL8fFojnX39ziHpaFma3tJPDt7YX9gT6lNaHvbFwYGzOY5j4LYugtOiFAACgYKAbkSARUSFQHGX2MipVE2THEXEdKLSCsqAIm91BoVAUF8yKqPVnz-4twaEMpbn04xGz0G0076",     
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PSID",
        "value": "g.a0004giE9A7E6ZsKFEL8fFojnX39ziHpaFma3tJPDt7YX9gT6lNaCYwmaaVyJrMyJqXfeJbujwACgYKASMSARUSFQHGX2Mi6-ehSAlKBXKmdzpeBUG7wBoVAUF8yKpp-8hCZrlyAVtQ4PsUDPq30076",     
        "domain": "google.com"
      },
      {
        "name": "SSID",
        "value": "ATjW7a4REiZbb9cFk",
        "domain": "google.com"
      },
      {
        "name": "SAPISID",
        "value": "yQeKVo0C_Rr3Bvai/A6WrGaxJ7Pmg8Z-li",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PAPISID",
        "value": "yQeKVo0C_Rr3Bvai/A6WrGaxJ7Pmg8Z-li",
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PAPISID",
        "value": "yQeKVo0C_Rr3Bvai/A6WrGaxJ7Pmg8Z-li",
        "domain": "google.com"
      },
      {
        "name": "AEC",
        "value": "AaJma5s_8GmhyNjHggAYs2Af9dQctH2f13p5fsJtPqXJ00mg77i71m3jwuY",
        "domain": "google.com"
      },
      {
        "name": "NID",
        "value": "527=TdjHoqO4ddlx0zzrhBWh0BShL4cM69ySqnH0LJD1bEDegk6_Wwu8cNceYuv2PulyJ0SwjzwT5int6Xa0Zna-td9BWSuwl4EILHJuPMu7Px41yIzRJX4sEhzGYUL-afZlGyZcrC5g7e_L7mi1c41he4swIg_7EYG9VFpOuznLgIGlSFmAhsNzmrTxXhgczkFOgPLzysaGHsTR8ei_UKSjSEq9lShj0Q_OAJbhydoIrUCnK-7TsaTHWJXMv4lRHRswrSj-Bhqz4gTEM2lJ_PPUhkhK0Jz8O56SCwYVmcPOlq3vUf_LCNI_CM6_YyoQM0gFlGZh2dYluYZQiXPjgJOBCs37WGu8P7-qOn3JDIvoTQZFNMxOu5Z3tceqvkkutRKBWMZ3UOLayvRKhkioXRtTMb5xogYzC_T4tMEgum8B9taSK0GCsZ2cZ3REcAgZd-uBWhrTEQIU50tWFex9oA_Mlm8-OSQz42tdsVeibOAHoDwtQ3rpCzp78d-zIud2UvDh4eiUi3yLP28qVQU5ybcFdqJ3HmErHmqzSqihT2yahMGBi1-Q9RMDTfvEkWzEXO5a18Ej4gxy4Tth13aS_o-1u0iXiWG5Zr9seXt_buWmnWaiV3yVNM9q8yOu9OlhRqjtsjKQGW2oIq4bQPexekS2W13ZST3gZQGUT65aD3gjF0a3SE50Erc4sbA6Sy0f1bXx1wmDmS2pguBYWkpzVM-TotAEwA8-WQoyV-jhHu0sb0xfv66FVpV8e3lWth7eoqpodXK-MmraUc8j1oYp93tGV3Gp8AMx8Sb9-AC0cJkwIdYpwD3LVapfYgHEFjAp0luvLrfkEBNNSyk0vV2ka_DVgmRjBOoLaHUMXtURLMGvxyIChwNKKs1cyLHBRwrdEg1vGjpUzlXouaIxwrw8rtkIusPesHijFIHw1jnfohZvtFb2sEmY41g2QjekVxaVES8debs7pfKDXvDnggeoPAv8bgDzcvF4P7DUi4mWloTlWxy9WK3D3EOgBAlWSNxZEfA66u3rfa9qUSmjx3v68g59Ag7MEbD_YHX0cvNJp2WMyZbHY6X5TSP9mulVzxNkGc8SUJU6YtA4Doc",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PSIDTS",
        "value": "sidts-CjEBflaCdY7wxlMUT5cib8fRSixGrZB3ycziCjnX5agB1rQh0rzjLQ-ksc0Ydcvj2NvZEAA",
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PSIDTS",
        "value": "sidts-CjEBflaCdY7wxlMUT5cib8fRSixGrZB3ycziCjnX5agB1rQh0rzjLQ-ksc0Ydcvj2NvZEAA",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PSIDCC",
        "value": "AKEyXzVSL5jkWCIRMWYO5NL-eftkaG9TnlBjUW2NsstmqZYrnszTtaksmt2kwsLZEzqQn72Zhpqg",
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PSIDCC",
        "value": "AKEyXzUFL6BwhNQ44mYBaiCmeAvQ5X6DGOS0xmJ7i_iftU-fhdPwpN4x7Vt47gDKTWjKyUEHULA",
        "domain": "google.com"
      }
    ],
    "gemini.google.com": [
      {
        "name": "COMPASS",
        "value": "gemini-pd=CjwACWuJV93jFYb_b6k1ZbZc5AVi75OXfwVJx6huPFdJgLZgT-iphNSBtyIyTho-2Gurv4U86El7hPmdVFUQyO6KygYaXQAJa4lXn9oi4Cbh75qeYR3VIE0BY5djWcUkAbEEzbhIu_LGieSlhyOewtmGSBpTT7Xb-poYs9ewAACTB5-VRmbP3P-ekagH_KMx5nISDa6_Ics_JeT9RdVB0hIHdSABMAE:gemini-hl=CkkACWuJV4Jq7gXnYGXm-CCWRGf1MNczIJ0yMsen8R98zb0fdd_v1HDcw_-Y0Gxw7WZu_GGVl89NUAGecp6EG6tM_DjudIlkdiK-ELfajMoGGmoACWuJV5CQ8pDAP50ezEOaV4OgrHoHttckpmemYdK1_oPE7fq21bvGOIBSxDUuDIlvAqiQIPlMfqXWkIDETvz2JlDdNgpTCCYe3tRksOoygjScyo251yEhQOJ4r8-frfSVO-h9Z-kSna0rIAEwAQ",
        "domain": "gemini.google.com"
      }
    ]
  }
}
PS C:\Users\motoc\gemini-api-wrapper> Invoke-RestMethod -Uri 'http://localhost:3000/api/cookies' -Method Get | ConvertTo-Json -Depth 5                             
{
  "success": true,
  "cookies": {
    "google.com": [
      {
        "name": "__Secure-BUCKET",
        "value": "CJ4D",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PSID",
        "value": "g.a0004giE9A7E6ZsKFEL8fFojnX39ziHpaFma3tJPDt7YX9gT6lNaHvbFwYGzOY5j4LYugtOiFAACgYKAbkSARUSFQHGX2MipVE2THEXEdKLSCsqAIm91BoVAUF8yKqPVnz-4twaEMpbn04xGz0G0076",     
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PSID",
        "value": "g.a0004giE9A7E6ZsKFEL8fFojnX39ziHpaFma3tJPDt7YX9gT6lNaCYwmaaVyJrMyJqXfeJbujwACgYKASMSARUSFQHGX2Mi6-ehSAlKBXKmdzpeBUG7wBoVAUF8yKpp-8hCZrlyAVtQ4PsUDPq30076",     
        "domain": "google.com"
      },
      {
        "name": "SSID",
        "value": "ATjW7a4REiZbb9cFk",
        "domain": "google.com"
      },
      {
        "name": "SAPISID",
        "value": "yQeKVo0C_Rr3Bvai/A6WrGaxJ7Pmg8Z-li",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PAPISID",
        "value": "yQeKVo0C_Rr3Bvai/A6WrGaxJ7Pmg8Z-li",
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PAPISID",
        "value": "yQeKVo0C_Rr3Bvai/A6WrGaxJ7Pmg8Z-li",
        "domain": "google.com"
      },
      {
        "name": "AEC",
        "value": "AaJma5s_8GmhyNjHggAYs2Af9dQctH2f13p5fsJtPqXJ00mg77i71m3jwuY",
        "domain": "google.com"
      },
      {
        "name": "NID",
        "value": "527=TdjHoqO4ddlx0zzrhBWh0BShL4cM69ySqnH0LJD1bEDegk6_Wwu8cNceYuv2PulyJ0SwjzwT5int6Xa0Zna-td9BWSuwl4EILHJuPMu7Px41yIzRJX4sEhzGYUL-afZlGyZcrC5g7e_L7mi1c41he4swIg_7EYG9VFpOuznLgIGlSFmAhsNzmrTxXhgczkFOgPLzysaGHsTR8ei_UKSjSEq9lShj0Q_OAJbhydoIrUCnK-7TsaTHWJXMv4lRHRswrSj-Bhqz4gTEM2lJ_PPUhkhK0Jz8O56SCwYVmcPOlq3vUf_LCNI_CM6_YyoQM0gFlGZh2dYluYZQiXPjgJOBCs37WGu8P7-qOn3JDIvoTQZFNMxOu5Z3tceqvkkutRKBWMZ3UOLayvRKhkioXRtTMb5xogYzC_T4tMEgum8B9taSK0GCsZ2cZ3REcAgZd-uBWhrTEQIU50tWFex9oA_Mlm8-OSQz42tdsVeibOAHoDwtQ3rpCzp78d-zIud2UvDh4eiUi3yLP28qVQU5ybcFdqJ3HmErHmqzSqihT2yahMGBi1-Q9RMDTfvEkWzEXO5a18Ej4gxy4Tth13aS_o-1u0iXiWG5Zr9seXt_buWmnWaiV3yVNM9q8yOu9OlhRqjtsjKQGW2oIq4bQPexekS2W13ZST3gZQGUT65aD3gjF0a3SE50Erc4sbA6Sy0f1bXx1wmDmS2pguBYWkpzVM-TotAEwA8-WQoyV-jhHu0sb0xfv66FVpV8e3lWth7eoqpodXK-MmraUc8j1oYp93tGV3Gp8AMx8Sb9-AC0cJkwIdYpwD3LVapfYgHEFjAp0luvLrfkEBNNSyk0vV2ka_DVgmRjBOoLaHUMXtURLMGvxyIChwNKKs1cyLHBRwrdEg1vGjpUzlXouaIxwrw8rtkIusPesHijFIHw1jnfohZvtFb2sEmY41g2QjekVxaVES8debs7pfKDXvDnggeoPAv8bgDzcvF4P7DUi4mWloTlWxy9WK3D3EOgBAlWSNxZEfA66u3rfa9qUSmjx3v68g59Ag7MEbD_YHX0cvNJp2WMyZbHY6X5TSP9mulVzxNkGc8SUJU6YtA4Doc",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PSIDTS",
        "value": "sidts-CjEBflaCdY7wxlMUT5cib8fRSixGrZB3ycziCjnX5agB1rQh0rzjLQ-ksc0Ydcvj2NvZEAA",
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PSIDTS",
        "value": "sidts-CjEBflaCdY7wxlMUT5cib8fRSixGrZB3ycziCjnX5agB1rQh0rzjLQ-ksc0Ydcvj2NvZEAA",
        "domain": "google.com"
      },
      {
        "name": "__Secure-1PSIDCC",
        "value": "AKEyXzVSL5jkWCIRMWYO5NL-eftkaG9TnlBjUW2NsstmqZYrnszTtaksmt2kwsLZEzqQn72Zhpqg",
        "domain": "google.com"
      },
      {
        "name": "__Secure-3PSIDCC",
        "value": "AKEyXzUFL6BwhNQ44mYBaiCmeAvQ5X6DGOS0xmJ7i_iftU-fhdPwpN4x7Vt47gDKTWjKyUEHULA",
        "domain": "google.com"
      }
    ],
    "gemini.google.com": [
      {
        "name": "COMPASS",
        "value": "gemini-pd=CjwACWuJV93jFYb_b6k1ZbZc5AVi75OXfwVJx6huPFdJgLZgT-iphNSBtyIyTho-2Gurv4U86El7hPmdVFUQyO6KygYaXQAJa4lXn9oi4Cbh75qeYR3VIE0BY5djWcUkAbEEzbhIu_LGieSlhyOewtmGSBpTT7Xb-poYs9ewAACTB5-VRmbP3P-ekagH_KMx5nISDa6_Ics_JeT9RdVB0hIHdSABMAE:gemini-hl=CkkACWuJV4Jq7gXnYGXm-CCWRGf1MNczIJ0yMsen8R98zb0fdd_v1HDcw_-Y0Gxw7WZu_GGVl89NUAGecp6EG6tM_DjudIlkdiK-ELfajMoGGmoACWuJV5CQ8pDAP50ezEOaV4OgrHoHttckpmemYdK1_oPE7fq21bvGOIBSxDUuDIlvAqiQIPlMfqXWkIDETvz2JlDdNgpTCCYe3tRksOoygjScyo251yEhQOJ4r8-frfSVO-h9Z-kSna0rIAEwAQ",
        "domain": "gemini.google.com"
      }
    ]
  }
}
PS C:\Users\motoc\gemini-api-wrapper> 


エンドポイントを追加したので、このクッキーを読み込んで、これをプロセス内で使用のこと
# Gemini Cookie設定（Chromeから取得）
GEMINI_1PSID=g.a0004giE9A7E6ZsKFEL8fFojnX39ziHpaFma3tJPDt7YX9gT6lNaHvbFwYGzOY5j4LYugtOiFAACgYKAbkSARUSFQHGX2MipVE2THEXEdKLSCsqAIm91BoVAUF8yKqPVnz-4twaEMpbn04xGz0G0076
GEMINI_1PSIDTS=sidts-CjEBflaCdUBEjqEv66NZCZrI8L6YxkCGc_mEbmInWkFjk-dOMwkJodyfKd-_wSagcaEgEAA

