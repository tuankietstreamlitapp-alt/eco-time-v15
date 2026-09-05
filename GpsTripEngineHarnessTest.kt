package vn.xeom4567.gps

import kotlin.math.*
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 4567 Xe Ôm — GPS / Trip Engine Test Harness
 *
 * Purpose:
 * - Exercise the GPS filtering math without needing a real phone or GPS.
 * - Compare the current V3 point-to-point rule with a candidate buffered rule.
 * - Protect core invariants before changing production GPS code.
 *
 * NOTE: CandidateBufferedEngine is test-only. It is NOT wired into production.
 */
class GpsTripEngineHarnessTest {

    data class GpsPoint(
        val lat: Double,
        val lon: Double,
        val elapsedMs: Long,
        val accuracyM: Double = 5.0,
        val reportedSpeedMps: Double? = null,
    )

    private val accuracyMaxM = 50.0
    private val minMoveM = 3.0
    private val maxSpeedMps = 45.0
    private val maxSegmentM = 250.0

    /** Mirrors the CURRENT production V3 behavior for diagnostic comparison. */
    private class CurrentV3Engine(
        private val accuracyMaxM: Double,
        private val minMoveM: Double,
        private val maxSpeedMps: Double,
        private val maxSegmentM: Double,
    ) {
        private var last: GpsPoint? = null
        var totalMeters: Double = 0.0
            private set

        fun resetAnchor() { last = null }

        fun add(point: GpsPoint) {
            if (!point.accuracyM.isFinite() || point.accuracyM <= 0.0 || point.accuracyM > accuracyMaxM) return
            val prev = last
            if (prev == null) {
                last = point
                return
            }

            val distance = haversineMeters(prev.lat, prev.lon, point.lat, point.lon)
            val dt = max(0.5, (point.elapsedMs - prev.elapsedMs) / 1000.0)
            val geometricSpeed = distance / dt
            val speedToCheck = point.reportedSpeedMps?.takeIf { it.isFinite() && it >= 0.0 } ?: geometricSpeed

            if (distance < minMoveM) {
                // This is the current V3 behavior that can erase slow-motion distance.
                last = point
                return
            }
            if (distance > maxSegmentM || speedToCheck > maxSpeedMps) return

            totalMeters += distance
            last = point
        }
    }

    /**
     * TEST-ONLY candidate algorithm.
     * It keeps the last committed anchor until the displacement reaches minMoveM,
     * so many small genuine movements can accumulate without turning every tiny GPS
     * jitter into distance.
     */
    private class CandidateBufferedEngine(
        private val accuracyMaxM: Double,
        private val minMoveM: Double,
        private val maxSpeedMps: Double,
        private val maxSegmentM: Double,
    ) {
        private var anchor: GpsPoint? = null
        var totalMeters: Double = 0.0
            private set

        fun resetAnchor() { anchor = null }

        fun add(point: GpsPoint) {
            if (!point.accuracyM.isFinite() || point.accuracyM <= 0.0 || point.accuracyM > accuracyMaxM) return
            val base = anchor
            if (base == null) {
                anchor = point
                return
            }

            val displacement = haversineMeters(base.lat, base.lon, point.lat, point.lon)
            val dt = max(0.5, (point.elapsedMs - base.elapsedMs) / 1000.0)
            val geometricSpeed = displacement / dt
            val speedToCheck = point.reportedSpeedMps?.takeIf { it.isFinite() && it >= 0.0 } ?: geometricSpeed

            if (displacement > maxSegmentM || speedToCheck > maxSpeedMps) return
            if (displacement < minMoveM) return

            totalMeters += displacement
            anchor = point
        }
    }

    @Test
    fun stationaryJitter_must_not_create_distance() {
        val engine = CandidateBufferedEngine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)
        val center = GpsPoint(10.0, 106.0, 0L)
        engine.add(center)

        // Jitter stays within ~1.5 m of the anchor.
        val offsets = listOf(-1.0, 0.8, -1.2, 1.1, -0.7, 0.9, -1.3, 1.0)
        offsets.forEachIndexed { i, metres ->
            engine.add(GpsPoint(
                lat = 10.0 + metres / 111_320.0,
                lon = 106.0,
                elapsedMs = (i + 1L) * 1000L,
            ))
        }

        assertEquals("Standing still with sub-threshold jitter must stay at 0 m", 0.0, engine.totalMeters, 0.01)
    }

    @Test
    fun slowWalking_should_accumulate_small_steps() {
        val current = CurrentV3Engine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)
        val candidate = CandidateBufferedEngine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)

        val points = (0..20).map { i ->
            GpsPoint(
                lat = 10.0 + (i * 1.0) / 111_320.0,
                lon = 106.0,
                elapsedMs = i.toLong() * 1000L,
            )
        }
        points.forEach { current.add(it); candidate.add(it) }

        // The legacy engine loses sub-3m steps; keep the assertion as a diagnostic fact.
        assertEquals("Legacy engine should lose these <3m steps", 0.0, current.totalMeters, 0.01)

        assertTrue(
            "Candidate engine should recover slow walking distance. actual=${candidate.totalMeters}m",
            candidate.totalMeters >= 18.0,
        )
    }

    @Test
    fun normalWalking_should_be_close_to_expected_distance() {
        val engine = CandidateBufferedEngine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)
        val points = (0..10).map { i ->
            GpsPoint(
                lat = 10.0 + (i * 10.0) / 111_320.0,
                lon = 106.0,
                elapsedMs = i.toLong() * 2000L,
            )
        }
        points.forEach(engine::add)
        assertEquals("10 × 10m ≈ 100m", 100.0, engine.totalMeters, 1.0)
    }

    @Test
    fun poorAccuracy_must_never_add_distance() {
        val engine = CandidateBufferedEngine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)
        engine.add(GpsPoint(10.0, 106.0, 0L, accuracyM = 5.0))
        engine.add(GpsPoint(10.0 + 100.0 / 111_320.0, 106.0, 2000L, accuracyM = 99.0))
        assertEquals(0.0, engine.totalMeters, 0.01)
    }

    @Test
    fun implausibleJump_must_not_add_distance() {
        val engine = CandidateBufferedEngine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)
        engine.add(GpsPoint(10.0, 106.0, 0L, accuracyM = 5.0))
        // 500m in one second is deliberately beyond the segment/speed policy.
        engine.add(GpsPoint(10.0 + 500.0 / 111_320.0, 106.0, 1000L, accuracyM = 5.0))
        assertEquals(0.0, engine.totalMeters, 0.01)
    }

    @Test
    fun pauseResume_must_reset_anchor() {
        val engine = CandidateBufferedEngine(accuracyMaxM, minMoveM, maxSpeedMps, maxSegmentM)
        engine.add(GpsPoint(10.0, 106.0, 0L))
        engine.add(GpsPoint(10.0 + 20.0 / 111_320.0, 106.0, 2000L))
        assertEquals(20.0, engine.totalMeters, 0.5)

        // Simulate PAUSE → RESUME anchor reset.
        engine.resetAnchor()
        engine.add(GpsPoint(10.0 + 200.0 / 111_320.0, 106.0, 20_000L))
        // No distance is added merely because the anchor changed during pause.
        assertEquals(20.0, engine.totalMeters, 0.5)

        engine.add(GpsPoint(10.0 + 220.0 / 111_320.0, 106.0, 22_000L))
        assertEquals(40.0, engine.totalMeters, 0.8)
    }

    private fun haversineMeters(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2).pow(2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2).pow(2)
        return r * 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
    }
}
