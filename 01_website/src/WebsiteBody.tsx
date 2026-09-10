import { content as c } from './content';
import { getProductionPoster } from './production-media';

const Arrow = ({ diagonal = false }: { diagonal?: boolean }) => (
  <span aria-hidden="true">{diagonal ? '↗' : '→'}</span>
);

export function WebsiteBody({
  replay,
  top,
}: {
  replay: () => void;
  top: () => void;
}) {
  return (
    <>
      <section
        id="services"
        className="services section"
        tabIndex={-1}
        aria-labelledby="services-title"
      >
        <div className="section-heading">
          <p className="eyebrow">01 / WHAT WE DO</p>
          <h2 id="services-title">
            車のことを、
            <br />
            ひとつずつ。
          </h2>
          <p className="section-intro">
            いつもの整備も、これからの車選びも。
            <br />
            お客様のご希望から、一緒に考えます。
          </p>
          <a className="text-link" href="#contact">
            車のことを相談する <Arrow />
          </a>
          <div className="service-note" aria-hidden="true">
            SERVICE
            <br />
            <span>&amp; CARE.</span>
          </div>
        </div>
        <div className="service-list">
          {c.services.map(([name, en, body], i) => (
            <article
              className="service-item"
              key={en}
              aria-labelledby={'service-' + i}
            >
              <span className="service-num" aria-hidden="true">
                0{i + 1}
              </span>
              <div className="service-detail">
                <h3 id={'service-' + i}>{name}</h3>
                <p className="service-en" lang="en">
                  {en}
                </p>
                <p className="service-description">{body}</p>
              </div>
              <a
                className="service-contact"
                href="#contact"
                aria-label={name + 'について相談する'}
              >
                <Arrow diagonal />
              </a>
            </article>
          ))}
        </div>
      </section>

      <section
        id="about"
        className="about section"
        tabIndex={-1}
        aria-labelledby="about-title"
      >
        <div className="about-visual">
          <figure className="about-image">
            <img
              src={
                getProductionPoster('desktop', 'tools') ??
                '/media/stage4/desktop/tools.jpg'
              }
              alt="工具が整然と並ぶ作業台を表現した3Dイメージ"
              width="1280"
              height="720"
              loading="lazy"
              decoding="async"
            />
            <figcaption>ONE CAR. ONE CONVERSATION.</figcaption>
          </figure>
          <figure className="about-detail-image">
            <img
              src={
                getProductionPoster('desktop', 'magazines') ??
                '/media/stage4/desktop/magazines.jpg'
              }
              alt="自動車雑誌が並ぶガラステーブルを表現した3Dイメージ"
              width="1280"
              height="720"
              loading="lazy"
              decoding="async"
            />
          </figure>
        </div>
        <div className="about-copy">
          <p className="eyebrow">02 / OUR APPROACH</p>
          <h2 id="about-title">
            大切にしているのは、
            <br />
            お客様のニーズです。
          </h2>
          <p>{c.introduction}</p>
          <p>
            日々の整備から、これからの車選びまで。
            <br />
            車との付き合い方を、あなたらしく。
          </p>
          <button className="text-link" onClick={replay}>
            もう一度、店舗を巡る <Arrow diagonal />
          </button>
        </div>
      </section>

      <section
        id="access"
        className="access section"
        tabIndex={-1}
        aria-labelledby="access-title"
      >
        <div className="access-heading">
          <p className="eyebrow">03 / FIND US</p>
          <h2 id="access-title">
            豊中で、
            <br />
            お待ちしています。
          </h2>
          <p className="location-type" aria-hidden="true">
            OSAKA
            <br />
            <span>TOYONAKA</span>
            <span className="location-marker">↗</span>
          </p>
        </div>
        <div className="shop-info">
          <p className="address">
            <span>大阪府</span>
            {c.address}
          </p>
          <a
            className="map-link"
            href={c.map}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>
              Google Mapsで場所を見る<small>別のタブで地図を開きます</small>
            </span>
            <Arrow diagonal />
          </a>
          <dl>
            <div>
              <dt>店舗名</dt>
              <dd>CAR PRODUCE ONE</dd>
            </div>
            <div>
              <dt>電話</dt>
              <dd>
                <a href={c.tel}>{c.phone}</a>
              </dd>
            </div>
            <div>
              <dt>FAX</dt>
              <dd>{c.fax}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section
        id="contact"
        className="contact section"
        tabIndex={-1}
        aria-labelledby="contact-title"
      >
        <div className="contact-heading">
          <p className="eyebrow">04 / LET’S TALK ABOUT YOUR CAR</p>
          <h2 id="contact-title">
            車のこと、
            <br />
            まずはお聞かせください。
          </h2>
          <p className="contact-lead">
            気になることや、これからの使い方。
            <br />
            お電話、またはLINEからご相談ください。
          </p>
        </div>
        <div className="contact-options">
          <a className="contact-option" href={c.tel}>
            <small>
              <span aria-hidden="true">01</span> 電話で相談する
            </small>
            <strong>{c.phone}</strong>
            <span className="contact-description">
              お話ししながら、ご希望をお聞かせください。
            </span>
            <span className="contact-arrow" aria-hidden="true">
              ↗
            </span>
          </a>
          <a
            className="contact-option"
            href={c.line}
            target="_blank"
            rel="noopener noreferrer"
          >
            <small>
              <span aria-hidden="true">02</span> LINEで相談する
            </small>
            <strong>
              LINE<span className="line-subtitle">メッセージで相談</span>
            </strong>
            <span className="contact-description">
              友だち追加の画面を別のタブで開きます。
            </span>
            <span className="contact-arrow" aria-hidden="true">
              ↗
            </span>
          </a>
        </div>
        <details className="qr">
          <summary>
            スマートフォンで読み取る
            <span className="qr-toggle" aria-hidden="true">
              ＋
            </span>
          </summary>
          <div className="qr-content">
            <img
              src="/media/line-qr.png"
              alt="CAR PRODUCE ONE LINE友だち追加QRコード"
              width="180"
              height="180"
              loading="lazy"
            />
            <p>
              スマートフォンのカメラで
              <br />
              QRコードを読み取ってください。
              <br />
              <a href={c.line} target="_blank" rel="noopener noreferrer">
                LINEの友だち追加画面を開く ↗
              </a>
            </p>
          </div>
        </details>
      </section>

      <footer className="site-footer">
        <div className="footer-brand">
          CAR PRODUCE ONE<span>AUTOMOTIVE / SERVICE &amp; CARE</span>
        </div>
        <nav className="footer-nav" aria-label="フッターナビゲーション">
          <a href="#services">サービス</a>
          <a href="#about">私たちについて</a>
          <a href="#access">アクセス</a>
          <a href="#contact">相談する</a>
        </nav>
        <div className="footer-bottom">
          <small>© CAR PRODUCE ONE</small>
          <button onClick={top}>
            ページの先頭へ <span aria-hidden="true">↑</span>
          </button>
        </div>
      </footer>
    </>
  );
}
