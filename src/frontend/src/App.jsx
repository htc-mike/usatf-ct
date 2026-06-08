import { HashRouter, Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation'
import Home from './pages/Home'
import Team from './pages/Team'
import Individual from './pages/Individual'
import Results from './pages/Results'

export default function App() {
  return (
    <HashRouter>
      <div className="min-h-screen bg-brand-light">
        <Navigation />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/team" element={<Team />} />
            <Route path="/individual" element={<Individual />} />
            <Route path="/results" element={<Results />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  )
}
