import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'

// المكونات
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import StockDetails from './pages/StockDetails'
import Recommendations from './pages/Recommendations'
import Watchlist from './pages/Watchlist'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/stock/:symbol" element={<StockDetails />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/watchlist" element={<Watchlist />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

