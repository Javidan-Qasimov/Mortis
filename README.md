# Homis

Flask, SQLAlchemy ve Socket.IO ile hazırlanmış gerçek zamanlı bire bir mesajlaşma demosu.

## Uçtan uca şifreleme prototipi

Yeni mesajlar tarayıcıda Web Crypto API ile ECDH P-256 üzerinden türetilen AES-256-GCM
anahtarıyla şifrelenir. Flask uygulaması yalnızca genel kimlik anahtarlarını, şifreli mesaj
zarfını ve mesajlaşma metadatasını (gönderen, alıcı, zaman) görür; özel anahtar veya mesaj
metnini almaz. Özel anahtar yalnızca kullanıcının o tarayıcısının local storage alanındadır.

Bu, **Signal Protocol değildir** ve Signal düzeyinde güvenlik iddia etmez. Signal'in resmi
tasarımı PQXDH/X3DH, ön anahtarlar, Double Ratchet, her mesaj için gelişen anahtarlar,
çoklu-cihaz oturum yönetimi ve uzun süreli güvenli anahtar saklama içerir. Bu prototipte
ileri gizlilik, ele geçirilme sonrası iyileşme, çoklu cihaz desteği ve anahtar güvenlik
numarası doğrulaması yoktur. Gerçek hassas iletişim ürünü için özel kripto tasarlamak yerine
denetlenmiş bir Signal Protocol istemci kütüphanesi ve bağımsız güvenlik denetimi kullanılmalıdır.

## Herhangi bir bilgisayarda çalıştırma

Docker Desktop yüklü olan bir bilgisayarda Python veya MySQL kurulumu gerekmez:

```powershell
git clone <GITHUB_REPOSITORY_URL>
cd <PROJE_KLASORU>
Copy-Item .env.example .env
# .env içindeki SECRET_KEY ve şifreleri güçlü, benzersiz değerlerle değiştirin.
docker compose up --build
```

Tarayıcıdan `http://localhost:5000` adresini açın. Uygulama varsayılan olarak yalnızca
aynı bilgisayardan erişilebilir. Durdurmak için `Ctrl+C`,
arka planda çalıştırıldıysa `docker compose down` kullanın. Veritabanı verisini de
silmek isterseniz `docker compose down -v` çalıştırın.

Adminer yalnızca gerektiğinde açılır:

```powershell
docker compose --profile tools up -d
```

Ardından `http://localhost:8080` adresinden erişilir.

## İnternetten erişilebilir bağlantı

GitHub yalnızca kaynak kodunu barındırır; canlı bağlantı için sürekli açık bir sunucu gerekir.
En taşınabilir seçenek, ücretsiz/ücretli bir VPS'e Docker ve Docker Compose kurup bu depoyu
klonlamak, production `.env` değerlerini ayarlamak, `APP_ENV=production`,
`FLASK_DEBUG=false`, `SESSION_COOKIE_SECURE=true` kullanmak ve uygulamayı HTTPS sağlayan
bir ters vekilin (Caddy veya Nginx) arkasında çalıştırmaktır. Bu durumda herkes alan adın
veya sunucu adresin üzerinden erişebilir; kişisel bilgisayarın açık olmak zorunda kalmaz.

`.env` dosyasını asla GitHub'a göndermeyin. Yalnız `.env.example` paylaşılır.

Geliştirme ortamında `AUTO_CREATE_SCHEMA=true` tabloları otomatik oluşturur. Production'da
`APP_ENV=production`, `FLASK_DEBUG=false`, `SESSION_COOKIE_SECURE=true` ve
`AUTO_CREATE_SCHEMA=false` kullanın. HTTPS arkasında production WSGI/ASGI sunucusu çalıştırın;
Flask'ın geliştirme sunucusunu kullanmayın.

## Şema değişiklikleri

Production şema değişikliklerini `create_all()` ile değil Flask-Migrate ile yönetin:

```powershell
cd backend
flask --app app db init
flask --app app db migrate -m "describe change"
flask --app app db upgrade
```

## Test

Proje kökünde `pytest` çalıştırın. Testler SQLite'ın geçici bellekteki veritabanını kullanır.

## Güvenlik notları

- `.env` Git'e eklenmez; yalnızca `.env.example` paylaşılır.
- MySQL ve Adminer portları yalnızca localhost'a bağlanır.
- Formlar CSRF korumalıdır; Socket.IO olaylarında alıcı doğrulaması, mesaj boyut sınırı ve işlem başına hız sınırı vardır.
- Çok işlemli production dağıtımında Socket.IO için paylaşımlı mesaj kuyruğu ve dağıtık rate-limit deposu (ör. Redis) yapılandırın.
