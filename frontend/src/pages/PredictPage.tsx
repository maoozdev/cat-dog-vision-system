import Predictor from '../components/Predictor'

export default function PredictPage() {
  return (
    <>
      <section className="page-header">
        <div>
          <h1>Image prediction</h1>
          <p className="muted">
            Choose an image or take a photo. If the model is unsure, it answers “Neither / Unknown”.
          </p>
        </div>
      </section>
      <div className="narrow">
        <Predictor />
      </div>
    </>
  )
}
