<script>
    import BarGraphs from './BarGraphs.svelte';
    import Home from './Home.svelte'
</script>

<main>
    <div id="main-vis-container">
        
        <!-- <div class="stars" /> -->

        <Home />

        <BarGraphs />
    </div>
</main>

<style>
  main {
    display: flex;
    align-items: center;
    justify-content: center;

    width : 100vw;
    height : 100vh;

    top : 0;
    left : 0;

    /* padding-left : 20px;
    padding-right : 20px; */

    /* border : 2px solid white; */

    overflow-x: hidden;
  }

  #main-vis-container {

    display : flex;
    align-items: center;
    justify-content: center;

    width : 100%;
    height : 100%;

    gap : 25px;

  }

  @keyframes twinkle {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.8; }
  }

  .stars {
        z-index: 2;
        position: fixed;
        top : 0;
        left : 0;
        width: 2px;
        height: 2px;
        background: white;
        border-radius: 50%;
        box-shadow:
            2vw 5vh white,
            10vw 20vh white,
            15vw 12vh white,
            20vw 40vh white,
            25vw 15vh white,
            30vw 50vh white,
            35vw 30vh white,
            40vw 60vh white,
            45vw 25vh white,
            50vw 10vh white,
            55vw 35vh white,
            60vw 45vh white,
            65vw 20vh white,
            70vw 50vh white,
            75vw 15vh white,
            80vw 40vh white,
            82vw 25vh white,
            85vw 35vh white,
            87vw 10vh white,
            90vw 45vh white,
            92vw 20vh white,
            94vw 50vh white,
            95vw 15vh white,
            96vw 40vh white,
            97vw 25vh white,
            98vw 35vh white,
            99vw 10vh white,
            1vw 50vh white,
            3vw 20vh white,
            5vw 50vh white,
            7vw 15vh white,
            9vw 40vh white,
            12vw 25vh white,
            14vw 35vh white,
            16vw 10vh white,
            18vw 45vh white,
            20vw 20vh white,
            22vw 50vh white,
            24vw 15vh white,
            26vw 40vh white,
            28vw 25vh white,
            30vw 35vh white,
            32vw 10vh white,
            34vw 45vh white,
            36vw 20vh white,
            38vw 50vh white,
            40vw 15vh white,
            42vw 40vh white,
            44vw 25vh white,
            46vw 35vh white,
            48vw 10vh white,
            50vw 45vh white,
            5vw 55vh white,
            15vw 60vh white,
            25vw 70vh white,
            35vw 80vh white,
            45vw 65vh white,
            55vw 75vh white,
            65vw 90vh white,
            75vw 85vh white,
            85vw 60vh white,
            95vw 95vh white,
            10vw 55vh white,
            20vw 65vh white,
            30vw 80vh white,
            40vw 75vh white,
            50vw 60vh white,
            60vw 85vh white,
            70vw 90vh white,
            80vw 95vh white,
            90vw 70vh white,
            10vw 95vh white,
            8vw 98vh white,
            20vw 99vh white,
            4vw 98vh white,
            100vw 60vh white;

        animation : twinkle 10s infinite ease-in-out alternate;
    }
</style>
